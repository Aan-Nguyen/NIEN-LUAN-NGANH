import struct
import os
import json 
from datetime import datetime, timedelta
import sys

# Tăng giới hạn đệ quy để cho phép quét thư mục sâu hơn (nếu cần)
# sys.setrecursionlimit(2000)

# === CONFIG (CẤU HÌNH) ===
# THAY ĐỔI: Sử dụng file image cục bộ. Đảm bảo file này tồn tại.
drive = r"\\.\F:"  # Đường dẫn tới file image ổ đĩa hoặc phân vùng FAT32
# Nơi lưu file báo cáo JSON
report_dir = r"C:\NLN\code\Machine-Learning-Forensic-Application" 

# === UTILITIES (TIỆN ÍCH) ===

def fat_dt_to_str(fat_date, fat_time, crt_tenth=0):
    """
    Chuyển đổi định dạng ngày/giờ FAT (date/time word) sang chuỗi "%d/%m/%Y %H:%M:%S".
    """
    if fat_date == 0 and fat_time == 0 and crt_tenth == 0:
        return ""

    # Chuyển đổi ngày
    year = ((fat_date >> 9) & 0x7F) + 1980
    month = (fat_date >> 5) & 0x0F
    day = fat_date & 0x1F
    
    # Chuyển đổi giờ
    hour = (fat_time >> 11) & 0x1F
    minute = (fat_time >> 5) & 0x3F
    second = (fat_time & 0x1F) * 2 

    try:
        dt = datetime(year, month, day, hour, minute, second)
        if crt_tenth > 0:
            dt += timedelta(milliseconds=crt_tenth * 10)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return "Invalid Date/Time"

# === I/O ===
def read_sector(f, sector, size=512):
    """Đọc một sector cụ thể từ file image."""
    f.seek(sector * size)
    return f.read(size)

# === BPB & layout ===
def parse_bpb(boot_sector):
    """Phân tích các trường quan trọng trong Boot Parameter Block (BPB)."""
    return {
        "bps":   struct.unpack("<H", boot_sector[11:13])[0], # Bytes per Sector
        "spc":   boot_sector[13],                            # Sectors per Cluster
        "res":   struct.unpack("<H", boot_sector[14:16])[0], # Reserved Sector Count
        "nfats": boot_sector[16],                            # Number of FATs
        "spf":   struct.unpack("<I", boot_sector[36:40])[0], # Sectors per FAT (FAT32)
        "root":  struct.unpack("<I", boot_sector[44:48])[0], # Root Directory Cluster (FAT32)
    }

def layout(start_lba, bpb):
    """Tính toán LBA của các khu vực chính. start_lba luôn là 0 cho file image."""
    fat0 = start_lba + bpb["res"]
    data = fat0 + bpb["nfats"] * bpb["spf"]
    return {"fat0": fat0, "data": data, "start_lba": start_lba}

# === cluster utilities ===
def first_sector_of_cluster(cluster, bpb, lay):
    """Tính toán LBA của sector đầu tiên của một cluster."""
    return lay["data"] + (cluster - 2) * bpb["spc"]

def read_cluster(f, cluster, bpb, lay):
    """Đọc toàn bộ dữ liệu của một cluster."""
    first_sector = first_sector_of_cluster(cluster, bpb, lay)
    f.seek(first_sector * bpb["bps"])
    return f.read(bpb["bps"] * bpb["spc"])

def read_fat_entry(f, cluster, bpb, lay):
    """Đọc entry 4 byte (FAT32) của một cluster trong FAT."""
    if cluster < 2: return 0xFFFFFFFF

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
    """
    Phân tích dữ liệu cluster thành các entry thư mục ngắn (SDE) và LFN,
    trích xuất tên đầy đủ, kích thước, cluster và date/time fields.
    """
    entries = []
    lfn_parts = [] # Dùng để tích lũy các phần của LFN

    for i in range(0, len(cluster_data), 32):
        e = cluster_data[i:i+32]
        if len(e) < 32 or e[0] == 0x00: 
            break
        
        attr = e[11]

        if attr == 0x0F: # LFN entry
            # Byte offsets của các phần tên Unicode (UTF-16LE)
            name_bytes = e[1:11] + e[14:26] + e[28:32]
            
            # Decode và loại bỏ ký tự rỗng/không hợp lệ
            lfn_part = name_bytes.decode('utf-16_le', errors='ignore')
            
            # Tiền tố (prepend) phần tên vào danh sách vì LFN được lưu ngược
            lfn_parts.insert(0, lfn_part) 
            continue # Chuyển sang entry tiếp theo

        # --- Dữ liệu SDE cơ bản ---
        # Đây là entry SDE (ngắn) cuối cùng của chuỗi LFN, hoặc là một entry 8.3
        
        deleted = (e[0] == 0xE5)
        name_sde = e[0:8].decode("ascii", errors="replace").strip()
        ext_sde = e[8:11].decode("ascii", errors="replace").strip()
        
        if lfn_parts:
            # Reconstruct tên đầy đủ, cắt sau ký tự kết thúc chuỗi LFN (\x00)
            fullname = "".join(lfn_parts).split('\x00', 1)[0]
            # Xóa các phần LFN đã tích lũy cho lần lặp tiếp theo
            lfn_parts = [] 
        else:
            # Fallback về tên 8.3 nếu không có chuỗi LFN nào được tìm thấy
            if deleted:
                # Tên file đã xóa (bắt đầu bằng '?')
                fullname = f"?{name_sde[1:]}.{ext_sde}" if ext_sde else f"?{name_sde[1:]}"
            else:
                fullname = f"{name_sde}.{ext_sde}" if ext_sde else name_sde
            
        clus_hi = struct.unpack("<H", e[20:22])[0]
        clus_low = struct.unpack("<H", e[26:28])[0]
        cluster = (clus_hi << 16) | clus_low
        size = struct.unpack("<I", e[28:32])[0]

        # --- Date/Time Raw Value Extraction ---
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
                # Lấy ext từ tên đầy đủ nếu có, nếu không thì dùng SDE ext
                "ext": fullname.split('.')[-1].upper() if '.' in fullname and fullname.split('.')[-1].upper() != fullname.upper() else ext_sde, 
                # Raw Date/Time values (dùng cho format)
                "crt_tenth": crt_tenth, "crt_time": crt_time, "crt_date": crt_date,
                "lst_acc_date": lst_acc_date, "lst_wrt_time": lst_wrt_time, "lst_wrt_date": lst_wrt_date,
            })
    return entries

# === quét & báo cáo ===
def check_file_status(f, start_cluster, size, bpb, lay):
    """Kiểm tra tình trạng phục hồi file dựa trên toàn bộ cluster cần thiết (theo size)."""
    cluster_size = bpb["bps"] * bpb["spc"]
    needed_clusters = (size + cluster_size - 1) // cluster_size 

    if needed_clusters == 0:
        return "Recoverable (Size 0)"

    free_cnt = 0
    
    # Giả định file chiếm các cluster liên tiếp
    for i in range(needed_clusters):
        current_cluster = start_cluster + i
        val = read_fat_entry(f, current_cluster, bpb, lay)
        
        if val is None:
            return "Unknown (FAT Read Error)"
            
        if val == 0: # Cluster rỗng
            free_cnt += 1
        # Các giá trị khác 0 là đang được sử dụng hoặc EOC

    if free_cnt == needed_clusters:
        return "Recoverable"
    elif free_cnt == 0:
        return "Overwritten"
    else:
        return "Partially Recoverable"

def scan_directory(f, cluster, bpb, lay, path=""):
    """Quét thư mục đệ quy và làm giàu metadata cho các file đã xóa."""
    
    try:
        data = read_cluster(f, cluster, bpb, lay)
    except IOError:
        print(f"[!] Lỗi I/O khi đọc cluster {cluster} tại đường dẫn: {path}. Bỏ qua.")
        return []

    entries = parse_directory_entries(data)

    results = []
    for e in entries:
        fullpath = os.path.join(path, e["name"])
        
        # --- Làm giàu dữ liệu ---
        offset = first_sector_of_cluster(e["cluster"], bpb, lay) * bpb["bps"] if e["cluster"] >= 2 else 0
        created_str = fat_dt_to_str(e["crt_date"], e["crt_time"], e["crt_tenth"])
        modified_str = fat_dt_to_str(e["lst_wrt_date"], e["lst_wrt_time"])
        accessed_str = fat_dt_to_str(e["lst_acc_date"], 0) 

        # --- Xử lý cho File/Thư mục đã xóa ---
        if e["deleted"] and e["cluster"] > 1:
            status = check_file_status(f, e["cluster"], e["size"], bpb, lay)
            
            # Xây dựng dictionary kết quả cuối cùng theo format yêu cầu
            enriched_entry = {
                "name": e["name"],
                "type": e["ext"].lower() if e["ext"] else "",
                "size": e["size"],
                "created": created_str,
                "modified": modified_str,
                "accessed": accessed_str,
                # Full path trong FAT chỉ là đường dẫn tương đối từ Root
                "full_path": fullpath, 
                "offset": offset,
                "start_cluster": e["cluster"],
                "status": status,
            }
            results.append(enriched_entry) 

        # --- Xử lý cho Thư mục thường (để tiếp tục quét đệ quy) ---
        if (e["attr"] & 0x10) and not e["deleted"] and e["cluster"] > 1:
            results.extend(scan_directory(f, e["cluster"], bpb, lay, fullpath))

    return results

# === MAIN (CHÍNH) ===
def main():
    try:
        # Mở file image ở chế độ nhị phân đọc
        with open(drive, "rb") as f:
            
            # Đối với file image, PBR nằm ở sector 0 của file
            start_lba = 0
            boot = read_sector(f, start_lba, 512)
            
            # Kiểm tra chữ ký FAT32
            if boot[510:512] != b'\x55\xaa':
                print("[!!!] Lỗi: Không tìm thấy chữ ký 0xAA55. File này có thể không phải là FAT32 image hợp lệ.")
                return

            bpb = parse_bpb(boot)
            lay = layout(start_lba, bpb)

            print(f"--- THÔNG TIN FAT32 IMAGE: {drive} ---")
            print(f"Bytes per Sector (BPS): {bpb['bps']}")
            print(f"Sectors per Cluster (SPC): {bpb['spc']}")
            print(f"Data Region LBA: {lay['data']}")
            print(f"Root Cluster: {bpb['root']}")
            print("------------------------------------------")
            
            # Bắt đầu quét tự động từ Root Directory (cluster mặc định)
            print("[*] Bắt đầu quét file đã xóa từ thư mục gốc (Deep Scan)...")
            deleted_files = scan_directory(f, bpb["root"], bpb, lay, "")
            print(f"[*] Hoàn tất quét. Tìm thấy {len(deleted_files)} file đã xóa.")

            # --- IN KẾT QUẢ VÀ CHUẨN BỊ XUẤT JSON ---
            if not deleted_files:
                print("\n[i] Không tìm thấy file đã xóa nào.")
                return

            print("\n=== KẾT QUẢ CÁC FILE ĐÃ XÓA ===")
            json_export_data = []
            for idx, e in enumerate(deleted_files, 1):
                json_export_data.append(e) 
                
                # In thông tin chi tiết
                print(f"--- FILE #{idx} ---")
                print(f"  Name: {e['name']} (.{e['type'].upper()})")
                print(f"  Size: {e['size']} bytes")
                print(f"  Start Cluster: {e['start_cluster']}")
                print(f"  Offset (Bytes): {e['offset']}")
                print(f"  Created: {e['created']}")
                print(f"  Modified: {e['modified']}")
                print(f"  Status: {e['status']}")
                
            # --- XUẤT RA JSON ---
            report_filename = "deleted_files.json"
            os.makedirs(report_dir, exist_ok=True)
            report_path = os.path.join(report_dir, report_filename)
            
            try:
                with open(report_path, "w", encoding="utf-8") as json_file:
                    json.dump(json_export_data, json_file, indent=4, ensure_ascii=False)
                
                print(f"\n[+] ĐÃ XUẤT BÁO CÁO JSON THÀNH CÔNG:")
                print(f"    Vị trí: {report_path}")
                
            except Exception as e:
                print(f"\n[!!!] Lỗi khi xuất file JSON: {e}")
                
    except FileNotFoundError:
        print(f"\n[!!!] Lỗi: Không tìm thấy file image '{drive}'. Vui lòng kiểm tra CONFIG.")
    except Exception as e:
        print(f"\n[!!!] Đã xảy ra lỗi không xác định: {e}")

if __name__ == "__main__":
    main()
