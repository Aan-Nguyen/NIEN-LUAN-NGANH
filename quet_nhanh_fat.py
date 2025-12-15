#!/usr/bin/env python3
import struct, check, os, json, sys
from datetime import datetime, timedelta

# Tăng giới hạn đệ quy để tránh lỗi với các thư mục quá sâu
sys.setrecursionlimit(5000)

# === UTILITIES (TIỆN ÍCH) ===

def fat_dt_to_str(fat_date, fat_time, crt_tenth=0):
    if fat_date == 0 and fat_time == 0 and crt_tenth == 0:
        return ""
    year = ((fat_date >> 9) & 0x7F) + 1980
    month = (fat_date >> 5) & 0x0F
    day = fat_date & 0x1F
    hour = (fat_time >> 11) & 0x1F
    minute = (fat_time >> 5) & 0x3F
    second = (fat_time & 0x1F) * 2
    try:
        dt = datetime(year, month, day, hour, minute, second)
        if crt_tenth > 0:
            dt += timedelta(milliseconds=crt_tenth * 10)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return ""

def read_sector(f, sector, size=512):
    f.seek(sector * size)
    return f.read(size)

# === BPB & layout ===
def parse_bpb(boot_sector):
    return {
        "bps": struct.unpack("<H", boot_sector[11:13])[0],
        "spc": boot_sector[13],
        "res": struct.unpack("<H", boot_sector[14:16])[0],
        "nfats": boot_sector[16],
        "spf": struct.unpack("<I", boot_sector[36:40])[0],
        "root": struct.unpack("<I", boot_sector[44:48])[0],
    }

def layout(start_lba, bpb):
    fat0 = start_lba + bpb["res"]
    data = fat0 + bpb["nfats"] * bpb["spf"]
    return {"fat0": fat0, "data": data, "start_lba": start_lba}

# === cluster utilities ===
def first_sector_of_cluster(cluster, bpb, lay):
    return lay["data"] + (cluster - 2) * bpb["spc"]

def read_cluster(f, cluster, bpb, lay):
    first_sector = first_sector_of_cluster(cluster, bpb, lay)
    f.seek(first_sector * bpb["bps"])
    return f.read(bpb["bps"] * bpb["spc"])

def read_fat_entry(f, cluster, bpb, lay):
    if cluster < 2:
        return 0xFFFFFFFF
    fat_offset = cluster * 4
    fat_sector = lay["fat0"] + (fat_offset // bpb["bps"])
    offset_in_sector = fat_offset % bpb["bps"]
    try:
        sec = read_sector(f, fat_sector, bpb["bps"])
        entry = struct.unpack("<I", sec[offset_in_sector:offset_in_sector+4])[0]
        return entry & 0x0FFFFFFF
    except (IOError, struct.error):
        return None

# === parse directory entries ===
def parse_directory_entries(cluster_data):
    entries = []
    lfn_parts = []
    for i in range(0, len(cluster_data), 32):
        e = cluster_data[i:i+32]
        if len(e) < 32 or e[0] == 0x00:
            break
        attr = e[11]
        if attr == 0x0F:
            name_bytes = e[1:11] + e[14:26] + e[28:32]
            lfn_part = name_bytes.decode('utf-16_le', errors='ignore')
            lfn_parts.insert(0, lfn_part)
            continue
        deleted = (e[0] == 0xE5)
        name_sde = e[0:8].decode("ascii", errors="replace").strip()
        ext_sde = e[8:11].decode("ascii", errors="replace").strip()
        if lfn_parts:
            fullname = "".join(lfn_parts).split('\x00', 1)[0]
            lfn_parts = []
        else:
            if deleted:
                fullname = f"?{name_sde[1:]}.{ext_sde}" if ext_sde else f"?{name_sde[1:]}"
            else:
                fullname = f"{name_sde}.{ext_sde}" if ext_sde else name_sde
        clus_hi = struct.unpack("<H", e[20:22])[0]
        clus_low = struct.unpack("<H", e[26:28])[0]
        cluster = (clus_hi << 16) | clus_low
        size = struct.unpack("<I", e[28:32])[0]
        crt_tenth = e[13]
        crt_time = struct.unpack("<H", e[14:16])[0]
        crt_date = struct.unpack("<H", e[16:18])[0]
        lst_acc_date = struct.unpack("<H", e[18:20])[0]
        lst_wrt_time = struct.unpack("<H", e[22:24])[0]
        lst_wrt_date = struct.unpack("<H", e[24:26])[0]
        if fullname not in [".", ".."]:
            entries.append({
                "name": fullname,
                "cluster": cluster,
                "size": size,
                "deleted": deleted,
                "attr": attr,
                "ext": fullname.split('.')[-1].lower() if '.' in fullname else ext_sde.lower(),
                "crt_tenth": crt_tenth, "crt_time": crt_time, "crt_date": crt_date,
                "lst_acc_date": lst_acc_date, "lst_wrt_time": lst_wrt_time, "lst_wrt_date": lst_wrt_date,
            })
    return entries

# === quét & báo cáo ===
def check_file_status(f, start_cluster, size, bpb, lay):
    cluster_size = bpb["bps"] * bpb["spc"]
    needed_clusters = (size + cluster_size - 1) // cluster_size
    if needed_clusters == 0:
        return "Recoverable (Size 0)"
    free_cnt = 0
    for i in range(needed_clusters):
        current_cluster = start_cluster + i
        val = read_fat_entry(f, current_cluster, bpb, lay)
        if val is None:
            return "Unknown (FAT Read Error)"
        if val == 0:
            free_cnt += 1
    if free_cnt == needed_clusters:
        return "Recoverable"
    elif free_cnt == 0:
        return "Overwritten"
    else:
        return "Partially Recoverable"

# === COUNT TOTAL ENTRIES PHASE (ĐỆ QUY) ===
def count_entries(f, cluster, bpb, lay, visited=None):
    """Đệ quy đếm tổng số entry (dùng để xác định denominator của progress)."""
    if visited is None:
        visited = set()
    try:
        if cluster in visited or cluster < 2:
            return 0
        visited.add(cluster)
        data = read_cluster(f, cluster, bpb, lay)
    except Exception:
        return 0

    entries = parse_directory_entries(data)
    total = len(entries)
    for e in entries:
        # nếu là thư mục (attr bit 0x10), chưa xóa, có cluster -> đệ quy
        if (e["attr"] & 0x10) and not e["deleted"] and e["cluster"] > 1:
            total += count_entries(f, e["cluster"], bpb, lay, visited)
    return total

# === SCAN (sử dụng progress_obj với total cố định) ===
def scan_directory(f, cluster, bpb, lay, path="", progress_obj=None, visited=None):
    """Quét thư mục đệ quy và gửi tiến độ. progress_obj phải có keys: done, total (total cố định)."""
    if progress_obj is None:
        progress_obj = {"done": 0, "total": 0}
    if visited is None:
        visited = set()
    try:
        if cluster in visited or cluster < 2:
            return []
        visited.add(cluster)
        data = read_cluster(f, cluster, bpb, lay)
    except IOError:
        return []

    entries = parse_directory_entries(data)
    results = []
    for e in entries:
        fullpath = os.path.join(path, e["name"])

        # Cập nhật done (chỉ done tăng, total KHÔNG đổi trong lúc scan)
        progress_obj["done"] += 1
        if progress_obj.get("total", 0) > 0:
            # Chỉ in progress khi thay đổi đáng kể để tránh lag console (optional, but good for performance)
            if progress_obj["done"] % 10 == 0 or progress_obj["done"] == progress_obj["total"]:
                percent = int((progress_obj["done"] / progress_obj["total"]) * 100)
                # In progress dưới dạng integer để dễ parse ở GUI
                print(f"PROGRESS {int(percent)}", flush=True)

        offset = first_sector_of_cluster(e["cluster"], bpb, lay) * bpb["bps"] if e["cluster"] >= 2 else 0
        created_str = fat_dt_to_str(e["crt_date"], e["crt_time"], e["crt_tenth"])
        modified_str = fat_dt_to_str(e["lst_wrt_date"], e["lst_wrt_time"])
        accessed_str = fat_dt_to_str(e["lst_acc_date"], 0)

        if e["deleted"] and e["cluster"] > 1:
            status = check_file_status(f, e["cluster"], e["size"], bpb, lay)
            
            # === [ĐOẠN CODE MỚI BẮT ĐẦU] ===
            integrity_val = "Unknown"
            
            # Chỉ check integrity nếu trạng thái cluster còn tốt ("Recoverable")
            # và kích thước file không quá lớn (<50MB) để tránh lag
            if status == "Recoverable" and 0 < e["size"] < 50 * 1024 * 1024:
                try:
                    # Lưu vị trí con trỏ hiện tại
                    current_pos = f.tell()
                    
                    # Tính offset của file trên ổ đĩa
                    # offset đã được tính ở dòng trên: offset = first_sector... * bps
                    
                    f.seek(offset)
                    raw_data = f.read(e["size"]) # Đọc dữ liệu lên RAM
                    
                    f.seek(current_pos) # Trả con trỏ về chỗ cũ
                    
                    # Gọi hàm check
                    score = check.analyze_file_integrity(raw_data, e["ext"])
                    
                    if score is None:
                        integrity_val = "N/A"
                    else:
                        integrity_val = f"{score:.2f}"
                        
                except Exception:
                    integrity_val = "Error"
            elif e["size"] == 0:
                integrity_val = "0.00"
            elif status != "Recoverable":
                integrity_val = "0.00" # Cluster đã bị ghi đè
            # === [ĐOẠN CODE MỚI KẾT THÚC] ===

            enriched_entry = {
                "name": e["name"],
                "type": e["ext"],
                "size": e["size"],
                "created": created_str,
                "modified": modified_str,
                "accessed": accessed_str,
                "full_path": fullpath,
                "offset": offset,
                "start_cluster": e["cluster"],
                "status": status,
                "integrity": integrity_val # <--- Thêm trường này vào JSON
            }
            results.append(enriched_entry)

        # nếu là thư mục con, đệ quy
        if (e["attr"] & 0x10) and not e["deleted"] and e["cluster"] > 1:
            results.extend(scan_directory(f, e["cluster"], bpb, lay, fullpath, progress_obj, visited))

    return results

# === MAIN (CHÍNH) ===
def main():
    if len(sys.argv) < 2:
        print("Usage: python quet_nhanh_fat.py <path_to_fat32_image_or_drive>")
        return

    image_path = sys.argv[1]
    
    try:
        with open(image_path, "rb") as f:
            start_lba = 0
            boot = read_sector(f, start_lba, 512)
            if boot[510:512] != b'\x55\xaa':
                print("[!!!] Lỗi: Không tìm thấy chữ ký 0xAA55. Có thể không phải FAT32 hợp lệ.")
                return

            bpb = parse_bpb(boot)
            lay = layout(start_lba, bpb)

            # --- Gửi tín hiệu ban đầu ---
            print("PROGRESS 0", flush=True)

            # Phase 1: Đếm tổng (có thể lâu)
            # In ra log để người dùng biết không bị treo
            # print("[DEBUG] Đang đếm số lượng file...", flush=True) 
            
            try:
                total_entries = count_entries(f, bpb["root"], bpb, lay)
            except Exception as e:
                total_entries = 1000 # Fallback nếu lỗi đếm

            if total_entries <= 0:
                total_entries = 1

            # Init progress obj with fixed total
            dprogress_obj = {"done": 0, "total": total_entries}

            # Phase 2: Quét thực sự
            deleted_files = scan_directory(f, bpb["root"], bpb, lay, "", dprogress_obj)

            # --- KẾT THÚC ---
            print("PROGRESS 100", flush=True)

            # --- XUẤT RA JSON ---
            try:
                with open("deleted_files.json", "w", encoding="utf-8") as json_file:
                    json.dump(deleted_files, json_file, indent=4, ensure_ascii=False)
                print(f"Xong! Tìm được {len(deleted_files)} file đã xóa.", flush=True)
            except Exception as e:
                print(f"[ERROR] Lỗi ghi JSON: {e}", flush=True)

    except FileNotFoundError:
        print(f"[ERROR] Không tìm thấy file: {image_path}", flush=True)
    except Exception as e:
        print(f"[ERROR] Lỗi không xác định: {e}", flush=True)

if __name__ == "__main__":
    main()