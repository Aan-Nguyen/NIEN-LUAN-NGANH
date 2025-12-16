import os, sys, json, io, check 
from PIL import Image

# ==============================
# ⚙️ Cấu hình cơ bản
# ==============================
CHUNK_SIZE = 128 * 1024 * 1024     # 4 MB (thực ra là 128MB theo code gốc)
MAX_BUFFER = 256 * 1024 * 1024    # 64 MB giữ buffer biên (thực ra là 256MB)
OUTPUT_DIR = "recovered_files"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================
# 🔍 Chữ ký file (head -> tail)
# ==============================
SIGNATURES = {
    "jpg":  {"head": b"\xFF\xD8", "tail": b"\xFF\xD9", "strategy": "simple", "ext":"jpg"},
    "png":  {"head": b"\x89PNG\r\n\x1a\n", "tail": b"IEND\xAE\x42\x60\x82", "strategy": "simple", "ext":"png"},
    "pdf":  {"head": b"%PDF-", "tail": b"%%EOF", "strategy": "pdf", "ext":"pdf"},
    "webp": {"head": b"RIFF", "tail": None, "strategy":"riff", "ext":"webp"},
    # Office dạng ZIP
    "docx": {"head": b"PK\x03\x04", "tail": b"PK\x05\x06", "strategy":"zip", "ext":"docx"},
    "xlsx": {"head": b"PK\x03\x04", "tail": b"PK\x05\x06", "strategy":"zip", "ext":"xlsx"},
    "pptx": {"head": b"PK\x03\x04", "tail": b"PK\x05\x06", "strategy":"zip", "ext":"pptx"},
}

ALL_HEADS = [v["head"] for v in SIGNATURES.values() if v.get("head")]

# ==============================
# 🧩 Hàm đọc an toàn
# ==============================
def safe_read(f, size):
    try:
        return f.read(size)
    except Exception:
        return b""

# 🧠 Kiểm tra hợp lệ
def is_valid_image(data, ftype):
    try:
        if ftype == "png":
            if not data.startswith(b"\x89PNG") or b"IHDR" not in data[:64]:
                return False
            if b"IEND" not in data:
                return False
        elif ftype == "jpg":
            img = Image.open(io.BytesIO(data))
            img.verify()
        return True
    except Exception:
        return False

def is_valid_pdf(data):
    return data.startswith(b"%PDF-") and b"%%EOF" in data[-2048:]

def is_valid_webp(data):
    if len(data) < 12:
        return False
    if not data.startswith(b"RIFF") or data[8:12] != b"WEBP":
        return False
    return True

def is_valid_office_zip(data, target):
    if not data.startswith(b"PK\x03\x04"):
        return False
    snippet = data[:4096]
    if target == "docx" and b"word/" in snippet:
        return True
    if target == "xlsx" and b"xl/" in snippet:
        return True
    if target == "pptx" and b"ppt/" in snippet:
        return True
    return False

# 📏 Hàm tìm tail
def find_tail_simple(buf, head_idx, tail):
    idx = buf.find(tail, head_idx + len(tail))
    return None if idx == -1 else idx + len(tail)

def find_tail_pdf(buf, head_idx, tail=None):
    idx = buf.find(b"%%EOF", head_idx)
    return None if idx == -1 else idx + len(b"%%EOF")

def find_tail_riff(buf, head_idx, tail=None):
    if len(buf) < head_idx + 12:
        return None
    size_field = int.from_bytes(buf[head_idx+4:head_idx+8], "little")
    end = head_idx + 8 + size_field
    return end if end < len(buf) else None

def find_tail_zip(buf, head_idx, tail=None):
    eocd = buf.find(b"PK\x05\x06", head_idx)
    return None if eocd == -1 else eocd + 22


TAIL_FINDERS = {
    "simple": find_tail_simple,
    "pdf": find_tail_pdf,
    "riff": find_tail_riff,
    "zip": find_tail_zip,
}


def carve_unified(source_path, max_scan_gb):
    print(f"Opening: {source_path}", flush=True)
    print("PROGRESS 0", flush=True)
    
    results = []
    buffer = b""
    
    # [QUAN TRỌNG] Biến theo dõi tổng số byte đã đọc từ file gốc
    total_bytes_read = 0 
    
    max_scan_bytes = max_scan_gb * 1024 * 1024 * 1024
    last_percent = -1

    try:
        with open(source_path, "rb") as f:
            while True:
                # Kiểm tra giới hạn quét
                if total_bytes_read >= max_scan_bytes:
                    break

                # Đọc chunk mới
                chunk = safe_read(f, CHUNK_SIZE)
                if not chunk:
                    break
                
                buffer += chunk
                total_bytes_read += len(chunk)

                # [QUAN TRỌNG] Tính offset của đầu buffer hiện tại
                # Buffer hiện tại bắt đầu tại vị trí: Tổng đã đọc - Độ dài buffer hiện có
                buffer_start_offset = total_bytes_read - len(buffer)

                # Duyệt qua các loại file cần tìm
                for key, sig in SIGNATURES.items():
                    search_pos = 0 # Vị trí tìm kiếm tương đối trong buffer
                    
                    while True:
                        # Tìm header
                        start_rel = buffer.find(sig["head"], search_pos)
                        if start_rel == -1:
                            break

                        # [QUAN TRỌNG] Tính Offset Tuyệt Đối CHÍNH XÁC
                        abs_offset = buffer_start_offset + start_rel

                        # Tìm tail
                        end_rel = TAIL_FINDERS[sig["strategy"]](buffer, start_rel, sig.get("tail"))
                        
                        # Nếu không tìm thấy tail, hoặc file quá lớn vượt buffer -> bỏ qua tạm thời
                        if end_rel is None:
                            # Nếu buffer đã quá lớn mà vẫn chưa thấy tail, có thể file lỗi hoặc quá to
                            # Ta skip header này để tránh vòng lặp vô tận
                            if len(buffer) >= MAX_BUFFER:
                                search_pos = start_rel + 1 
                                continue
                            else:
                                # Chưa đủ dữ liệu, thoát vòng lặp tìm kiếm để đọc thêm chunk mới
                                break
                        
                        # Trích xuất dữ liệu
                        data = buffer[start_rel:end_rel]

                        # [Logic Kiểm tra trùng lặp offset nếu cần thiết]
                        # (Bạn có thể thêm logic check seen_ranges ở đây nếu muốn)

                        # Xác thực dữ liệu (Validate)
                        ok = False
                        if key in ("jpg", "png"):
                            ok = is_valid_image(data, key)
                        elif key == "pdf":
                            ok = is_valid_pdf(data)
                        elif key == "webp":
                            ok = is_valid_webp(data)
                        elif key in ("docx", "xlsx", "pptx"):
                            ok = is_valid_office_zip(data, key)

                        if ok:
                            # Xuất file
                            filename = f"{key}_{abs_offset}.{sig['ext']}" # Đặt tên theo offset để dễ debug
                            out_path = os.path.join(OUTPUT_DIR, filename)
                            with open(out_path, "wb") as out:
                                out.write(data)

                            # Check Integrity
                            integrity_str = "N/A"
                            try:
                                integrity_score = check.analyze_file_integrity(out_path)
                                integrity_str = f"{integrity_score:.2f}"
                            except Exception as e:
                                integrity_str = f"Error: {e}"

                            # Ghi kết quả
                            entry = {
                                "name": filename,
                                "full_path": os.path.abspath(source_path),
                                "offset": abs_offset, # [CHÍNH XÁC]
                                "size": len(data),
                                "type": key,
                                "temp_path": os.path.abspath(out_path),
                                "integrity": integrity_str,
                                "status": "Carved"
                            }
                            entry["Chi tiết"] = entry.copy()
                            results.append(entry)
                            
                            # Cập nhật vị trí tìm kiếm tiếp theo
                            search_pos = end_rel
                        else:
                            # Nếu không valid, tìm tiếp từ ngay sau header
                            search_pos = start_rel + 1

                # [CƠ CHẾ TRƯỢT BUFFER - SLIDING WINDOW]
                # Giữ lại một phần cuối buffer để nối với chunk sau (phòng trường hợp file nằm giữa ranh giới 2 chunk)
                # Kích thước giữ lại nên lớn hơn kích thước file lớn nhất kỳ vọng (ví dụ 10MB) 
                # hoặc đơn giản là giữ lại một phần của MAX_BUFFER.
                
                KEEP_SIZE = 10 * 1024 * 1024 # Giữ lại 10MB cuối
                if len(buffer) > KEEP_SIZE:
                     buffer = buffer[-KEEP_SIZE:]
                
                # Cập nhật Progress
                if max_scan_bytes > 0:
                    percent = int((total_bytes_read / max_scan_bytes) * 100)
                    if percent > 100: percent = 100
                    if percent > last_percent:
                        print(f"PROGRESS {percent}", flush=True)
                        last_percent = percent

    except Exception as e:
        print(f"[❌] Error: {e}", flush=True)

    # Xuất JSON kết quả
    output_json = "deleted_files.json"
    with open(output_json, "w", encoding="utf-8") as jf:
        json.dump(results, jf, indent=2, ensure_ascii=False)
    
    print("PROGRESS 100", flush=True)
    print(f"[✅] Done. Found {len(results)} files.", flush=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python quet_sau.py <path> [GB]")
    else:
        drive = sys.argv[1]
        size = float(sys.argv[2]) if len(sys.argv) > 2 else 1
        carve_unified(drive, max_scan_gb=size)