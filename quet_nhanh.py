import pytsk3
import struct
import os
from datetime import datetime

# ================= Utils =================
def format_time(ts):
    if ts is None or ts == 0:
        return "N/A"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

def read_sector(f, sector, size=512):
    f.seek(sector * size)
    return f.read(size)

def parse_bpb(boot_sector):
    """Parse FAT32 Boot Sector"""
    return {
        "bytes_per_sector": struct.unpack("<H", boot_sector[11:13])[0],
        "sectors_per_cluster": boot_sector[13],
        "reserved_sectors": struct.unpack("<H", boot_sector[14:16])[0],
        "num_fats": boot_sector[16],
        "sectors_per_fat": struct.unpack("<I", boot_sector[36:40])[0],
        "root_cluster": struct.unpack("<I", boot_sector[44:48])[0]
    }

def fat_data_region_start(bpb):
    """Sector bắt đầu vùng dữ liệu"""
    return bpb["reserved_sectors"] + bpb["num_fats"] * bpb["sectors_per_fat"]

def cluster_to_offset(cluster, bpb):
    """Tính offset byte từ cluster"""
    data_start = fat_data_region_start(bpb)
    sector = data_start + (cluster - 2) * bpb["sectors_per_cluster"]
    return sector * bpb["bytes_per_sector"]

def read_fat_entry(f, cluster, bpb):
    fat_offset = cluster * 4
    fat_sector = bpb["reserved_sectors"] + (fat_offset // bpb["bytes_per_sector"])
    offset_in_sector = fat_offset % bpb["bytes_per_sector"]
    f.seek(fat_sector * bpb["bytes_per_sector"])
    sec = f.read(bpb["bytes_per_sector"])
    entry = struct.unpack("<I", sec[offset_in_sector:offset_in_sector+4])[0] & 0x0FFFFFFF
    return entry

def check_file_status(f, start_cluster, file_size, bpb):
    """Kiểm tra toàn bộ cluster của file"""
    if start_cluster is None or start_cluster <= 1:
        return "Unknown"
    cluster_size = bpb["bytes_per_sector"] * bpb["sectors_per_cluster"]
    total_clusters = (file_size + cluster_size - 1) // cluster_size
    current_cluster = start_cluster
    recovered_clusters = 0
    overwritten_clusters = 0

    for _ in range(total_clusters):
        entry = read_fat_entry(f, current_cluster, bpb)
        if entry == 0x00000000:
            recovered_clusters += 1
        else:
            overwritten_clusters += 1
        if entry >= 0x0FFFFFF8 or entry == 0x0FFFFFF7:
            break
        else:
            current_cluster = entry

    if recovered_clusters == total_clusters:
        return "Recoverable"
    elif overwritten_clusters == total_clusters:
        return "Overwritten"
    else:
        return "Partially Recoverable"

# ================= Core scan =================
def scan_deleted_fat_with_offset(image_path):
    results = []

    img = pytsk3.Img_Info(image_path)
    fs = pytsk3.FS_Info(img)
    f_raw = open(image_path, "rb")
    boot = read_sector(f_raw, 0)
    bpb = parse_bpb(boot)

    def walk_dir(directory, parent_path="/"):
        for entry in directory:
            if not hasattr(entry, "info") or not hasattr(entry.info, "name"):
                continue
            name = entry.info.name.name.decode(errors="ignore")
            if name in [".", ".."]:
                continue
            meta = entry.info.meta
            full_path = os.path.join(parent_path, name)

            if meta and meta.flags & pytsk3.TSK_FS_META_FLAG_UNALLOC:
                file_type = os.path.splitext(name)[1][1:] or "File"
                size = getattr(meta, "size", 0)
                ctime = format_time(meta.crtime)
                mtime = format_time(meta.mtime)
                start_cluster = getattr(meta, "addr", None)
                offset_bytes = cluster_to_offset(start_cluster, bpb) if start_cluster else None
                status = check_file_status(f_raw, start_cluster, size, bpb) if start_cluster else "Unknown"

                results.append({
                    "full_path": full_path,
                    "type": file_type,
                    "size": size,
                    "ctime": ctime,
                    "mtime": mtime,
                    "start_cluster": start_cluster,
                    "offset_bytes": offset_bytes,
                    "status": status
                })

            if meta and meta.type == pytsk3.TSK_FS_META_TYPE_DIR and not (meta.flags & pytsk3.TSK_FS_META_FLAG_UNALLOC):
                try:
                    subdir = entry.as_directory()
                    walk_dir(subdir, full_path)
                except Exception:
                    pass

    root = fs.open_dir(path="/")
    walk_dir(root)
    f_raw.close()
    return results

# ================= Main =================
if __name__ == "__main__":
    image_path = input("Nhập đường dẫn phân vùng hoặc file image: ").strip()
    files = scan_deleted_fat_with_offset(image_path)
    for idx, f in enumerate(files, 1):
        print(f"[{idx}] {f['full_path']} | Type: {f['type']} | Size: {f['size']} | Created: {f['ctime']} | Modified: {f['mtime']} | Offset: {f['offset_bytes']} | Status: {f['status']}")
