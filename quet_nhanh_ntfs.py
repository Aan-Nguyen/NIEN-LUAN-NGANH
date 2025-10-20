#!/usr/bin/env python3
# quet_sau_ntfs_full.py
import struct
import json
import datetime
import sys
import os

# === CẤU HÌNH MẶC ĐỊNH ===
PARTITION = r"\\.\D:"             # thay mặc định nếu muốn
OUT_JSON = "deleted_files.json"
BUFFER_SIZE = 1024 * 1024 * 4     # 4MB đọc theo cluster/run

# === HỖ TRỢ ===
def filetime_to_str(ft):
    """Chuyển FILETIME (Windows) sang chuỗi dd/MM/YYYY HH:MM:SS"""
    if not ft:
        return ""
    try:
        unix_ts = (ft - 116444736000000000) / 10000000
        dt = datetime.datetime.utcfromtimestamp(unix_ts)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return ""

    """Chuyển byte -> KB/MB/GB"""
    if size_bytes is None:
        return "0 B"
    size = float(size_bytes)
    if size < 1024:
        return f"{size:.0f} B"
    elif size < 1024**2:
        return f"{size/1024:.2f} KB"
    elif size < 1024**3:
        return f"{size/1024**2:.2f} MB"
    else:
        return f"{size/1024**3:.2f} GB"
# === ĐỌC BOOT SECTOR ===
def read_boot_sector(f):
    f.seek(0)
    boot = f.read(512)
    if len(boot) < 512:
        raise ValueError("Không đọc được boot sector (file quá nhỏ).")
    if boot[3:11] != b"NTFS    ":
        raise ValueError("Không phải phân vùng NTFS!")

    bytes_per_sector = struct.unpack_from("<H", boot, 0x0B)[0]
    sectors_per_cluster = boot[0x0D]
    cluster_mft = struct.unpack_from("<Q", boot, 0x30)[0]
    clusters_per_file_record_raw = struct.unpack_from("b", boot, 0x40)[0]

    cluster_size = bytes_per_sector * sectors_per_cluster
    if clusters_per_file_record_raw < 0:
        record_size = 2 ** abs(clusters_per_file_record_raw)
    else:
        record_size = clusters_per_file_record_raw * cluster_size

    return cluster_size, cluster_mft, record_size

# === PARSE DATA RUNS ===
def parse_data_run(content):
    pos = 0
    runs = []
    current_lcn = 0
    while pos < len(content):
        header = content[pos]
        if header == 0:
            break
        len_len = header & 0x0F
        off_len = header >> 4
        pos += 1
        if pos + len_len + off_len > len(content):
            break
        cluster_len = int.from_bytes(content[pos:pos + len_len], "little") if len_len > 0 else 0
        pos += len_len
        cluster_off_raw = int.from_bytes(content[pos:pos + off_len], "little", signed=True) if off_len > 0 else 0
        pos += off_len
        current_lcn += cluster_off_raw
        runs.append((current_lcn, cluster_len))
    return runs

# === Lấy real_size và data runs của $MFT từ record 0 ===
def get_mft_runs_and_size(f, mft_offset, record_size):
    f.seek(mft_offset)
    rec = f.read(record_size)
    if not rec or rec[0:4] != b"FILE":
        return None, None

    attr_off = struct.unpack_from("<H", rec, 0x14)[0]
    pos = attr_off
    runs = None
    real_size = None

    while pos + 8 < len(rec):
        attr_type = struct.unpack_from("<I", rec, pos)[0]
        if attr_type == 0xFFFFFFFF:
            break
        attr_len = struct.unpack_from("<I", rec, pos + 4)[0]
        if attr_len == 0:
            break
        non_resident = rec[pos + 8]

        # DATA attribute (0x80)
        if attr_type == 0x80 and non_resident == 1:
            # offset to data runs: at pos + 0x20 (2 bytes) in attribute header
            try:
                data_run_offset = struct.unpack_from("<H", rec, pos + 0x20)[0]
                real_size = struct.unpack_from("<Q", rec, pos + 0x30)[0]
                data_run_start = pos + data_run_offset
                data_run_content = rec[data_run_start: pos + attr_len]
                runs = parse_data_run(data_run_content)
                return runs, real_size
            except Exception:
                return None, None
        pos += attr_len

    return None, None

# === Đọc một record MFT theo logical offset trong file $MFT (bytes) ===
def read_record_from_mft_runs(f, runs, cluster_size, record_size, logical_offset):
    # chuẩn bị cumulative sizes
    cum = 0
    for (lcn, length) in runs:
        run_bytes = length * cluster_size
        if logical_offset >= cum and logical_offset < cum + run_bytes:
            # record nằm trong run này
            offset_into_run = logical_offset - cum
            # physical offset trên disk (bytes)
            disk_offset = lcn * cluster_size + offset_into_run
            f.seek(disk_offset)
            data = f.read(record_size)
            if len(data) < record_size:
                return None
            return data
        cum += run_bytes
    return None

# === Trích ATTR FILE_NAME từ 1 record (dùng để build parent tree) ===
def extract_file_name_from_record(record):
    try:
        if not record or record[0:4] != b"FILE":
            return None, None, "", "", ""
        attr_off = struct.unpack_from("<H", record, 0x14)[0]
        pos = attr_off
        while pos + 8 < len(record):
            attr_type = struct.unpack_from("<I", record, pos)[0]
            if attr_type == 0xFFFFFFFF:
                break
            attr_len = struct.unpack_from("<I", record, pos + 4)[0]
            if attr_len == 0 or pos + attr_len > len(record):
                break
            non_resident = record[pos + 8]
            # FILE_NAME resident attribute
            if attr_type == 0x30 and non_resident == 0:
                content_size = struct.unpack_from("<I", record, pos + 16)[0]
                content_offset = struct.unpack_from("<H", record, pos + 20)[0]
                content = record[pos + content_offset: pos + content_offset + content_size]
                if len(content) >= 0x42:
                    parent_ref = struct.unpack_from("<Q", content, 0x00)[0] & 0xFFFFFFFFFFFF
                    name_len = content[0x40]
                    name_raw = content[0x42:0x42 + name_len * 2]
                    filename = name_raw.decode("utf-16le", errors="ignore")
                    created = filetime_to_str(struct.unpack_from("<Q", content, 0x10)[0])
                    modified = filetime_to_str(struct.unpack_from("<Q", content, 0x18)[0])
                    accessed = filetime_to_str(struct.unpack_from("<Q", content, 0x20)[0])
                    return parent_ref, filename, created, modified, accessed
            pos += attr_len
    except Exception:
        pass
    return None, None, "", "", ""

# === Trích DATA attribute non-resident để lấy start cluster và real_size của file trong record ===
def extract_data_info_from_record(record):
    try:
        if not record or record[0:4] != b"FILE":
            return None, 0
        attr_off = struct.unpack_from("<H", record, 0x14)[0]
        pos = attr_off
        while pos + 8 < len(record):
            attr_type = struct.unpack_from("<I", record, pos)[0]
            if attr_type == 0xFFFFFFFF:
                break
            attr_len = struct.unpack_from("<I", record, pos + 4)[0]
            if attr_len == 0 or pos + attr_len > len(record):
                break
            non_resident = record[pos + 8]
            if attr_type == 0x80 and non_resident == 1:
                # lấy data runs
                data_run_offset = struct.unpack_from("<H", record, pos + 0x20)[0]
                real_size = struct.unpack_from("<Q", record, pos + 0x30)[0]
                data_run_start = pos + data_run_offset
                data_run_content = record[data_run_start: pos + attr_len]
                runs = parse_data_run(data_run_content)
                if runs and len(runs) > 0:
                    start_cluster = runs[0][0]
                    return start_cluster, real_size
                else:
                    return None, real_size
            pos += attr_len
    except Exception:
        pass
    return None, 0

# === XÂY DỰNG PARENT TREE TỪ TOÀN BỘ RECORD MFT ===
def build_parent_tree_from_runs(f, runs, cluster_size, record_size, max_records=None):
    tree = {}
    # tính tổng byte của MFT theo runs
    total_bytes = sum(length * cluster_size for (_, length) in runs)
    total_records = total_bytes // record_size
    # đọc từng record bằng cách dịch logical offset
    for rec_idx in range(total_records):
        logical_offset = rec_idx * record_size
        record = read_record_from_mft_runs(f, runs, cluster_size, record_size, logical_offset)
        if not record:
            continue
        parent_ref, filename, _, _, _ = extract_file_name_from_record(record)
        if filename:
            tree[rec_idx] = {"name": filename, "parent": parent_ref}
        if max_records and rec_idx >= max_records:
            break
    return tree, total_records

# === PHÂN TÍCH MỘT RECORD (dùng để ghi kết quả nếu file bị xóa) ===
def parse_mft_record_by_bytes(record, rec_idx, cluster_size, tree):
    try:
        if not record or record[0:4] != b"FILE":
            return None
        flags = struct.unpack_from("<H", record, 0x16)[0]
        in_use = bool(flags & 0x01)
        # chỉ lấy file đã xóa -> in_use == False
        if in_use:
            return None

        # trích attribute FILE_NAME và DATA
        parent_ref = 0
        filename = None
        created = modified = accessed = ""
        file_size = 0
        offset = 0
        start_cluster = None

        attr_off = struct.unpack_from("<H", record, 0x14)[0]
        pos = attr_off
        while pos + 8 < len(record):
            attr_type = struct.unpack_from("<I", record, pos)[0]
            if attr_type == 0xFFFFFFFF:
                break
            attr_len = struct.unpack_from("<I", record, pos + 4)[0]
            if attr_len == 0 or pos + attr_len > len(record):
                break
            non_resident = record[pos + 8]

            if attr_type == 0x30 and non_resident == 0:
                # FILE_NAME
                content_size = struct.unpack_from("<I", record, pos + 16)[0]
                content_offset = struct.unpack_from("<H", record, pos + 20)[0]
                content = record[pos + content_offset: pos + content_offset + content_size]
                p_ref, filename, created, modified, accessed = extract_file_name_from_record(record)
                if filename:
                    parent_ref = p_ref

            elif attr_type == 0x80 and non_resident == 1:
                # DATA non-resident
                data_run_offset = struct.unpack_from("<H", record, pos + 0x20)[0]
                real_size = struct.unpack_from("<Q", record, pos + 0x30)[0]
                file_size = real_size
                data_run_start = pos + data_run_offset
                data_run_content = record[data_run_start: pos + attr_len]
                runs = parse_data_run(data_run_content)
                if runs and len(runs) > 0:
                    start_cluster = runs[0][0]
                    offset = start_cluster * cluster_size
            pos += attr_len

        if not filename:
            return None
        if offset == 0:
            # không có offset (có thể resident hoặc không có data) -> bỏ
            return None

        ext = os.path.splitext(filename)[1].replace(".", "").lower()
        full_path = build_full_path_from_tree(parent_ref, tree)

        return {
            "name": filename,
            "type": ext,
            "size": file_size,
            "created": created,
            "modified": modified,
            "accessed": accessed,
            "full_path": full_path,
            "offset": offset,
            "start_cluster": start_cluster,
            "status": "Deleted"
        }
    except Exception:
        return None

# === XÂY DỰNG ĐƯỜNG DẪN HOÀN CHỈNH TỪ record_num CHA ===
def build_full_path(record_num, tree):
    path_parts = []
    current = record_num
    for _ in range(100):
        if current not in tree:
            break
        entry = tree[current]
        name = entry.get("name", "")
        path_parts.insert(0, name)
        parent = entry.get("parent", 0)
        # parent is file reference: top 48 bits = sequence? but earlier we stored masked already
        current = parent
        if current == 5:
            break
    return "\\".join(path_parts)

# alias to match previous name used
build_full_path_from_tree = build_full_path

# === HÀM CHÍNH ===
def main():
    partition = PARTITION
    if len(sys.argv) >= 2:
        partition = sys.argv[1]

    if not os.path.exists(partition):
        print("[!] Partition path không tồn tại:", partition)
        return

    results = []
    try:
        with open(partition, "rb") as f:
            # đọc boot
            cluster_size, mft_cluster, record_size = read_boot_sector(f)
            mft_offset = mft_cluster * cluster_size
            print(f"[*] Cluster size: {cluster_size}, MFT cluster: {mft_cluster}, record size: {record_size}")
            print(f"[*] MFT byte offset (logical): {mft_offset}")

            # lấy runs và real size của $MFT
            runs, real_size = get_mft_runs_and_size(f, mft_offset, record_size)
            if runs is None or real_size is None:
                # fallback: nếu không lấy được, cảnh báo và dừng (an toàn)
                return

            total_mft_bytes = real_size
            total_clusters = sum(length for (_, length) in runs)
            # tổng số record MFT
            total_records = total_mft_bytes // record_size

            # build parent tree (từ toàn bộ runs)
            tree, rec_count = build_parent_tree_from_runs(f, runs, cluster_size, record_size, max_records=None)
            # duyệt từng record và parse file đã xóa
            for rec_idx in range(total_records):
                logical_offset = rec_idx * record_size
                record = read_record_from_mft_runs(f, runs, cluster_size, record_size, logical_offset)
                if not record:
                    continue
                parsed = parse_mft_record_by_bytes(record, rec_idx, cluster_size, tree)
                if parsed:
                    results.append(parsed)

            # ghi kết quả
            with open(OUT_JSON, "w", encoding="utf-8") as jf:
                json.dump(results, jf, ensure_ascii=False, indent=2)
            print(f"\n✅ Done. Found {len(results)} deleted files. Saved to {OUT_JSON}")

    except PermissionError:
        print("[!!!] Permission denied. Hãy chạy script với quyền Administrator/root.")
    except Exception as e:
        print(f"[!!!] Unexpected error: {e}")

if __name__ == "__main__":
    main()