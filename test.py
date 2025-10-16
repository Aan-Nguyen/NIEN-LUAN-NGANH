# raw_disk_scan.py
# Chạy trên Windows với quyền Administrator
# Không dùng thư viện ngoài: dùng ctypes, struct, json, os

import ctypes
import struct
import json
import os

# Cấu hình
MAX_DRIVES = 8             # Số PhysicalDrive thử mở (tăng nếu cần)
SECTOR_SIZE_DEFAULT = 512   # nếu không xác định được, tạm dùng 512

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3

# ctypes helpers
LARGE_INTEGER = ctypes.c_longlong
LPARGE_INTEGER = ctypes.POINTER(LARGE_INTEGER)

def open_physical_drive(n):
    """Mở handle tới \\.\PhysicalDriven (wchar)"""
    path = r"\\.\PhysicalDrive{}".format(n)
    # CreateFileW expects wchar
    CreateFileW = kernel32.CreateFileW
    CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_uint,
                            ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p]
    CreateFileW.restype = ctypes.c_void_p

    handle = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
    if handle == ctypes.c_void_p(-1).value or handle is None:
        return None
    return handle

def close_handle(h):
    kernel32.CloseHandle(ctypes.c_void_p(h))

def get_disk_size(handle):
    """GetFileSizeEx -> returns size in bytes (int)"""
    GetFileSizeEx = kernel32.GetFileSizeEx
    GetFileSizeEx.argtypes = [ctypes.c_void_p, LPARGE_INTEGER]
    GetFileSizeEx.restype = ctypes.c_bool
    size = LARGE_INTEGER(0)
    ok = GetFileSizeEx(ctypes.c_void_p(handle), ctypes.byref(size))
    if not ok:
        return None
    return int(size.value)

def set_file_pointer(handle, offset):
    """SetFilePointerEx to move file pointer to offset"""
    SetFilePointerEx = kernel32.SetFilePointerEx
    SetFilePointerEx.argtypes = [ctypes.c_void_p, LARGE_INTEGER, LPARGE_INTEGER, ctypes.c_uint]
    SetFilePointerEx.restype = ctypes.c_bool
    newpos = LARGE_INTEGER(0)
    ok = SetFilePointerEx(ctypes.c_void_p(handle), LARGE_INTEGER(offset), ctypes.byref(newpos), 0)
    return ok

def read_from_handle(handle, size, offset=None):
    """Read 'size' bytes from handle; if offset specified, seek first."""
    if offset is not None:
        if not set_file_pointer(handle, offset):
            raise OSError("SetFilePointerEx failed")
    # ReadFile
    ReadFile = kernel32.ReadFile
    ReadFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint), ctypes.c_void_p]
    ReadFile.restype = ctypes.c_bool
    buf = ctypes.create_string_buffer(size)
    read = ctypes.c_uint(0)
    ok = ReadFile(ctypes.c_void_p(handle), ctypes.byref(buf), ctypes.c_uint(size), ctypes.byref(read), None)
    if not ok:
        raise OSError("ReadFile failed")
    return buf.raw[:read.value]

# --- MBR parsing ---
def parse_mbr_sector(sector_data, sector_size):
    """
    sector_data: bytes of sector 0
    returns list of partitions: dicts with start_lba, num_sectors, type, boot_flag
    """
    if len(sector_data) < 512:
        return []
    # signature 0x55AA at offset 510
    sig = sector_data[510:512]
    if sig != b'\x55\xAA':
        # not a valid MBR signature, still attempt
        pass

    parts = []
    for i in range(4):
        off = 446 + i * 16
        entry = sector_data[off:off+16]
        boot_flag = entry[0]
        part_type = entry[4]
        start_lba = struct.unpack_from("<I", entry, 8)[0]
        num_sectors = struct.unpack_from("<I", entry, 12)[0]
        if part_type == 0x00 or num_sectors == 0:
            continue
        parts.append({
            "index": i,
            "boot": bool(boot_flag == 0x80),
            "type": part_type,
            "start_lba": start_lba,
            "num_sectors": num_sectors,
            "offset_bytes": start_lba * sector_size,
            "length_bytes": num_sectors * sector_size
        })
    return parts

# --- GPT parsing ---
def parse_gpt_header(header_bytes):
    """
    Parse GPT header (expected at LBA1, i.e., bytes from offset = sector_size)
    returns dict with fields or None if not GPT
    """
    if len(header_bytes) < 92:
        return None
    sig = header_bytes[0:8]
    if sig != b"EFI PART":
        return None
    # little-endian values
    revision = struct.unpack_from("<I", header_bytes, 8)[0]
    header_size = struct.unpack_from("<I", header_bytes, 12)[0]
    current_lba = struct.unpack_from("<Q", header_bytes, 24)[0]
    backup_lba = struct.unpack_from("<Q", header_bytes, 32)[0]
    first_usable = struct.unpack_from("<Q", header_bytes, 40)[0]
    last_usable = struct.unpack_from("<Q", header_bytes, 48)[0]
    disk_guid = header_bytes[56:72]  # 16 bytes
    part_entry_lba = struct.unpack_from("<Q", header_bytes, 72)[0]
    num_part_entries = struct.unpack_from("<I", header_bytes, 80)[0]
    part_entry_size = struct.unpack_from("<I", header_bytes, 84)[0]

    return {
        "revision": revision,
        "header_size": header_size,
        "current_lba": current_lba,
        "backup_lba": backup_lba,
        "first_usable_lba": first_usable,
        "last_usable_lba": last_usable,
        "disk_guid_raw": disk_guid,
        "part_entry_lba": part_entry_lba,
        "num_part_entries": num_part_entries,
        "part_entry_size": part_entry_size
    }

def guid_to_str(raw):
    # raw is 16 bytes little-endian fields per GPT spec
    if len(raw) != 16:
        return ""
    d = struct.unpack("<IHH8B", raw)
    hexs = "{:08x}-{:04x}-{:04x}-{:02x}{:02x}-{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}".format(
        d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8], d[9], d[10]
    )
    return hexs

def parse_gpt_partition_entry(entry_bytes):
    # GPT partition entry layout: type GUID (16), unique GUID (16), first LBA (8), last LBA (8), attrs (8), name (72=36 UTF-16)
    if len(entry_bytes) < 128:
        return None
    type_guid = entry_bytes[0:16]
    unique_guid = entry_bytes[16:32]
    first_lba = struct.unpack_from("<Q", entry_bytes, 32)[0]
    last_lba = struct.unpack_from("<Q", entry_bytes, 40)[0]
    attrs = struct.unpack_from("<Q", entry_bytes, 48)[0]
    name_raw = entry_bytes[56:56+72]
    # name is UTF-16LE, trim trailing zeros
    try:
        name = name_raw.decode("utf-16le").rstrip("\x00")
    except Exception:
        name = ""
    return {
        "type_guid": guid_to_str(type_guid),
        "unique_guid": guid_to_str(unique_guid),
        "first_lba": first_lba,
        "last_lba": last_lba,
        "attributes": attrs,
        "name": name,
        "start_lba": first_lba,
        "num_lba": (last_lba - first_lba + 1) if last_lba >= first_lba else 0
    }

# --- Main scan function ---
def scan_physical_drives(max_drives=MAX_DRIVES):
    result = {"disks": []}
    for d in range(max_drives):
        handle = open_physical_drive(d)
        if not handle:
            # can't open this drive - skip
            continue
        try:
            total_size = get_disk_size(handle)
            if total_size is None:
                close_handle(handle)
                continue
            # sector size: we assume default 512; better detection can be added
            sector_size = SECTOR_SIZE_DEFAULT

            size_gb = round(total_size / (1024**3), 2)
            disk_entry = {
                "physical_name": f"PhysicalDrive{d}",
                "drive_index": d,
                "total_size": total_size,
                "size_gb": size_gb,
                "sector_size": sector_size,
                "volumes": []
            }

            # read sector 0 (MBR)
            try:
                mbr = read_from_handle(handle, sector_size, 0)
            except Exception as e:
                mbr = b""
            parts = parse_mbr_sector(mbr, sector_size)
            # detect protective MBR (type 0xEE indicates GPT present)
            is_protective = any(p.get("type") == 0xEE for p in parts)
            if is_protective:
                # read GPT header at LBA 1
                try:
                    gpt_header = read_from_handle(handle, sector_size, sector_size * 1)
                except Exception as e:
                    gpt_header = b""
                gpt = parse_gpt_header(gpt_header)
                if gpt:
                    # read partition entries (num_entry * entry_size) starting at part_entry_lba
                    entries = []
                    base_lba = gpt["part_entry_lba"]
                    num = gpt["num_part_entries"]
                    entry_size = gpt["part_entry_size"]
                    # read in chunks (limit size)
                    total_bytes = num * entry_size
                    try:
                        raw = read_from_handle(handle, total_bytes, base_lba * sector_size)
                    except Exception:
                        # if too big, read in pieces
                        raw = b""
                        for i in range(num):
                            try:
                                ebytes = read_from_handle(handle, entry_size, (base_lba + i * (entry_size//sector_size)) * sector_size)
                                raw += ebytes
                            except Exception:
                                break
                    # parse entries
                    for i in range(num):
                        off = i * entry_size
                        entry_bytes = raw[off:off+entry_size]
                        if len(entry_bytes) < entry_size:
                            break
                        pe = parse_gpt_partition_entry(entry_bytes)
                        if not pe:
                            continue
                        if pe["num_lba"] <= 0:
                            continue
                        pe["offset_bytes"] = pe["start_lba"] * sector_size
                        pe["length_bytes"] = pe["num_lba"] * sector_size
                        entries.append(pe)
                    # attach entries
                    for e in entries:
                        disk_entry["volumes"].append({
                            "label": e.get("name", ""),
                            "filesystem": "",   # needs FS parsing
                            "start_lba": e["start_lba"],
                            "num_lba": e["num_lba"],
                            "offset": e["offset_bytes"],
                            "size_gb": round(e["length_bytes"] / (1024**3), 2),
                            "type_guid": e.get("type_guid", "")
                        })
                else:
                    # cannot parse GPT header -> fallback to MBR parts
                    for p in parts:
                        disk_entry["volumes"].append({
                            "label": "",
                            "filesystem": "",
                            "start_lba": p["start_lba"],
                            "num_lba": p["num_sectors"],
                            "offset": p["offset_bytes"],
                            "size_gb": round(p["length_bytes"] / (1024**3), 2),
                            "type": p["type"]
                        })
            else:
                # non-GPT MBR partitions
                for p in parts:
                    disk_entry["volumes"].append({
                        "label": "",
                        "filesystem": "",
                        "start_lba": p["start_lba"],
                        "num_lba": p["num_sectors"],
                        "offset": p["offset_bytes"],
                        "size_gb": round(p["length_bytes"] / (1024**3), 2),
                        "type": p["type"]
                    })

            result["disks"].append(disk_entry)
        finally:
            close_handle(handle)
    return result

if __name__ == "__main__":
    if os.name != "nt":
        print("Script này chỉ chạy trên Windows.")
        raise SystemExit(1)

    # Cần chạy với Admin
    try:
        data = scan_physical_drives(MAX_DRIVES)
        out = "disk_info_raw.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved to {out}")
    except PermissionError:
        print("Bạn cần chạy script với quyền Administrator.")
    except Exception as e:
        print("Lỗi:", e)
