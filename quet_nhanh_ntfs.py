#!/usr/bin/env python3
# quet_sau_ntfs_full.py

import struct, json, datetime, sys, os, check

# === CẤU HÌNH ===
OUT_JSON = "deleted_files.json"

# === HỖ TRỢ ===

def filetime_to_str(ft):
    """Chuyển FILETIME → chuỗi dd/MM/YYYY HH:MM:SS"""
    if not ft:
        return ""
    try:
        unix_ts = (ft - 116444736000000000) / 10000000
        dt = datetime.datetime.utcfromtimestamp(unix_ts)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return ""


def format_size(size_bytes):
    """Chuyển số byte → KB/MB/GB"""
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
        raise ValueError("Không đọc được boot sector.")
    if boot[3:11] != b"NTFS    ":
        raise ValueError("Không phải phân vùng NTFS.")

    bytes_per_sector = struct.unpack_from("<H", boot, 0x0B)[0]
    sectors_per_cluster = boot[0x0D]
    cluster_mft = struct.unpack_from("<Q", boot, 0x30)[0]
    clusters_per_file_record_raw = struct.unpack_from("b", boot, 0x40)[0]

    cluster_size = bytes_per_sector * sectors_per_cluster
    if clusters_per_file_record_raw < 0:
        record_size = 1 << abs(clusters_per_file_record_raw)
    else:
        record_size = clusters_per_file_record_raw * cluster_size

    return cluster_size, cluster_mft, record_size


# === PARSE DATA RUN ===

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

        cluster_len = int.from_bytes(content[pos:pos + len_len], "little") if len_len else 0
        pos += len_len

        cluster_off_raw = int.from_bytes(content[pos:pos + off_len], "little", signed=True) if off_len else 0
        pos += off_len

        current_lcn += cluster_off_raw
        runs.append((current_lcn, cluster_len))
    return runs


# === LẤY RUNS TỪ RECORD $MFT ===

def get_mft_runs_and_size(f, mft_offset, record_size):
    f.seek(mft_offset)
    rec = f.read(record_size)
    if not rec or rec[0:4] != b"FILE":
        return None, None

    attr_off = struct.unpack_from("<H", rec, 0x14)[0]
    pos = attr_off

    while pos + 8 < len(rec):
        attr_type = struct.unpack_from("<I", rec, pos)[0]
        if attr_type == 0xFFFFFFFF:
            break
        attr_len = struct.unpack_from("<I", rec, pos + 4)[0]
        if attr_len == 0:
            break

        non_resident = rec[pos + 8]

        if attr_type == 0x80 and non_resident == 1:
            data_run_offset = struct.unpack_from("<H", rec, pos + 0x20)[0]
            real_size = struct.unpack_from("<Q", rec, pos + 0x30)[0]
            start = pos + data_run_offset
            data = rec[start:pos + attr_len]
            runs = parse_data_run(data)
            return runs, real_size

        pos += attr_len

    return None, None


# === ĐỌC RECORD TỪ RUNS ===

def read_record_from_mft_runs(f, runs, cluster_size, record_size, logical_offset):
    cum = 0
    for (lcn, length) in runs:
        run_bytes = length * cluster_size
        if cum <= logical_offset < cum + run_bytes:
            inside = logical_offset - cum
            disk_offset = lcn * cluster_size + inside
            f.seek(disk_offset)
            data = f.read(record_size)
            return data if len(data) == record_size else None
        cum += run_bytes
    return None


# === EXTRACT FILE_NAME ===

def extract_file_name_from_record(record):
    try:
        if record[0:4] != b"FILE":
            return None, None, "", "", ""
        attr_off = struct.unpack_from("<H", record, 0x14)[0]
        pos = attr_off
        while pos + 8 < len(record):
            attr_type = struct.unpack_from("<I", record, pos)[0]
            if attr_type == 0xFFFFFFFF:
                break
            attr_len = struct.unpack_from("<I", record, pos + 4)[0]
            if attr_len == 0:
                break

            if attr_type == 0x30 and record[pos + 8] == 0:
                csize = struct.unpack_from("<I", record, pos + 16)[0]
                coff = struct.unpack_from("<H", record, pos + 20)[0]
                content = record[pos + coff:pos + coff + csize]

                parent = struct.unpack_from("<Q", content, 0)[0] & 0xFFFFFFFFFFFF
                name_len = content[0x40]
                name = content[0x42:0x42 + name_len * 2].decode("utf-16le", errors="ignore")
                created = filetime_to_str(struct.unpack_from("<Q", content, 0x10)[0])
                modified = filetime_to_str(struct.unpack_from("<Q", content, 0x18)[0])
                accessed = filetime_to_str(struct.unpack_from("<Q", content, 0x20)[0])

                return parent, name, created, modified, accessed

            pos += attr_len
    except:
        pass
    return None, None, "", "", ""


# === DATA ATTRIBUTE ===

def extract_data_info_from_record(record):
    try:
        if record[0:4] != b"FILE":
            return None, 0

        attr_off = struct.unpack_from("<H", record, 0x14)[0]
        pos = attr_off
        while pos + 8 < len(record):
            attr_type = struct.unpack_from("<I", record, pos)[0]
            if attr_type == 0xFFFFFFFF:
                break
            attr_len = struct.unpack_from("<I", record, pos + 4)[0]

            if attr_type == 0x80 and record[pos + 8] == 1:
                off = struct.unpack_from("<H", record, pos + 0x20)[0]
                real = struct.unpack_from("<Q", record, pos + 0x30)[0]
                content = record[pos + off:pos + attr_len]
                runs = parse_data_run(content)

                if runs:
                    return runs[0][0], real
                return None, real

            pos += attr_len
    except:
        pass
    return None, 0


# === XÂY DỰNG PARENT TREE ===

def build_parent_tree_from_runs(f, runs, cluster_size, record_size, max_records=None):
    tree = {}
    total_bytes = sum(length * cluster_size for (_, length) in runs)
    total_records = total_bytes // record_size

    for rec_idx in range(total_records):
        logical = rec_idx * record_size
        record = read_record_from_mft_runs(f, runs, cluster_size, record_size, logical)
        if not record:
            continue
        parent, name, *_ = extract_file_name_from_record(record)
        if name:
            tree[rec_idx] = {"name": name, "parent": parent}
        if max_records and rec_idx >= max_records:
            break

    return tree, total_records


def build_full_path(rec_no, tree):
    parts = []
    cur = rec_no
    for _ in range(100):
        if cur not in tree:
            break
        entry = tree[cur]
        parts.insert(0, entry["name"])
        cur = entry["parent"]
        if cur == 5:
            break
    return "\\".join(parts)


# Alias
build_full_path_from_tree = build_full_path


# === PARSE RECORD ===

def parse_mft_record_by_bytes(record, rec_idx, cluster_size, tree):
    try:
        if record[0:4] != b"FILE":
            return None

        flags = struct.unpack_from("<H", record, 0x16)[0]
        if flags & 1:  # in_use = True
            return None

        parent, name, created, modified, accessed = extract_file_name_from_record(record)
        if not name:
            return None

        start_cluster, file_size = extract_data_info_from_record(record)
        if not start_cluster:
            return None

        offset = start_cluster * cluster_size
        ext = os.path.splitext(name)[1].replace(".", "").lower()
        full_path = build_full_path_from_tree(parent, tree)

        return {
            "name": name,
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

    except:
        return None

# === CHƯƠNG TRÌNH CHÍNH ===

def main():
    if len(sys.argv) < 2:
        print("Sử dụng: python quet_nhanh_ntfs.py <đường_dẫn_ảnh_phân_vùng_NTFS>")
        return

    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print("Không tìm thấy file.")
        return

    results = []

    try:
        with open(image_path, "rb") as f:
            cluster_size, mft_cluster, record_size = read_boot_sector(f)
            mft_offset = mft_cluster * cluster_size

            runs, real_size = get_mft_runs_and_size(f, mft_offset, record_size)
            if not runs:
                print("Không đọc được RUN của MFT.")
                return

            total_records = real_size // record_size
            
            # Gửi tín hiệu bắt đầu
            print("PROGRESS 0", flush=True)

            # Bước 1: Xây dựng cây thư mục (Bước này cũng tốn thời gian, nhưng tạm thời chưa báo progress để đơn giản)
            # Nếu muốn kỹ hơn, bạn có thể chia progress: 30% cho build tree, 70% cho parse.
            tree, _ = build_parent_tree_from_runs(f, runs, cluster_size, record_size)

            # Bước 2: Quét và Parse (Đây là bước lâu nhất)
            for rec_idx in range(total_records):
                
                # --- THÊM ĐOẠN NÀY ĐỂ BÁO TIẾN ĐỘ ---
                if rec_idx % 1000 == 0: # Cứ mỗi 1000 records thì báo 1 lần để đỡ lag
                    if total_records > 0:
                        percent = int((rec_idx / total_records) * 100)
                        print(f"PROGRESS {percent}", flush=True)
                # ------------------------------------

                logical = rec_idx * record_size
                record = read_record_from_mft_runs(f, runs, cluster_size, record_size, logical)
                if not record:
                    continue
                parsed = parse_mft_record_by_bytes(record, rec_idx, cluster_size, tree)
                if parsed:
                    integrity_val = "Unknown"
                    try:
                        # Chỉ check nếu file có kích thước hợp lý (>0 và <50MB để tránh treo)
                        f_size = parsed["size"]
                        f_offset = parsed["offset"]
                        f_ext = parsed["type"]
                        
                        if f_size > 0 and f_size < 50 * 1024 * 1024:
                            current_pos = f.tell() # Lưu vị trí cũ
                            f.seek(f_offset)       # Nhảy tới vị trí file
                            raw_data = f.read(f_size) # Đọc dữ liệu lên RAM
                            f.seek(current_pos)    # Quay lại vị trí cũ
                            
                            # Gọi hàm check từ bộ nhớ
                            # Lưu ý: check.py mới phải hỗ trợ đọc bytes (như code mình đưa ở trên)
                            score = check.analyze_file_integrity(raw_data, f_ext)
                            integrity_val = f"{score:.2f}"
                        elif f_size >= 50 * 1024 * 1024:
                            integrity_val = "Skipped (Too Large)"
                        else:
                            integrity_val = "0" # File rỗng
                            
                    except Exception as e:
                        integrity_val = ""
                    
                    # Thêm vào dict kết quả
                    parsed["integrity"] = integrity_val
                    # =======================

                    results.append(parsed)

        # Gửi tín hiệu kết thúc 100%
        print("PROGRESS 100", flush=True)

        with open(OUT_JSON, "w", encoding="utf-8") as jf:
            json.dump(results, jf, ensure_ascii=False, indent=2)

        print(f"Xong! Tìm được {len(results)} file đã xóa.", flush=True)

    except Exception as e:
        print(f"[LỖI] {e}")

if __name__ == "__main__":
    main()
