import os, sys, json, io
from PIL import Image

# ==============================
# ⚙️ Cấu hình cơ bản
# ==============================
CHUNK_SIZE = 128 * 1024 * 1024     # 4 MB mỗi lần đọc
MAX_BUFFER = 256 * 1024 * 1024    # 64 MB giữ buffer biên
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
    print(f"[+] Bắt đầu quét: {source_path}")
    results, seen_ranges = [], []
    buffer = b""
    file_offset_base = 0
    max_scan_bytes = max_scan_gb * 1024 * 1024 * 1024

    try:
        with open(source_path, "rb") as f:
            while True:
                if file_offset_base >= max_scan_bytes:
                    print(f"[i] Dừng sau {max_scan_gb} GB (demo).")
                    break

                chunk = safe_read(f, CHUNK_SIZE)
                if not chunk:
                    break
                buffer += chunk

                for key, sig in SIGNATURES.items():
                    start = 0
                    while True:
                        start = buffer.find(sig["head"], start)
                        if start == -1:
                            break

                        end = TAIL_FINDERS[sig["strategy"]](buffer, start, sig.get("tail"))
                        if end is None:
                            break

                        abs_offset = file_offset_base + start
                        data = buffer[start:end]

                        if any(s <= abs_offset <= e for s, e in seen_ranges):
                            start = end
                            continue

                        # Xác thực
                        ok = False
                        if key in ("jpg", "png"):
                            ok = is_valid_image(data, key)
                        elif key == "pdf":
                            ok = is_valid_pdf(data)
                        elif key == "webp":
                            ok = is_valid_webp(data)
                        elif key in ("docx", "xlsx", "pptx"):
                            ok = is_valid_office_zip(data, key)

                        if not ok:
                            start = end
                            continue

                        # Xuất file tạm
                        filename = f"{key}_{len(results)+1}.{sig['ext']}"
                        out_path = os.path.join(OUTPUT_DIR, filename)
                        with open(out_path, "wb") as out:
                            out.write(data)

                        seen_ranges.append((abs_offset, abs_offset + len(data)))

                        # Ghi thông tin đầy đủ
                        results.append({
                            "name": filename,
                            "full_path": os.path.abspath(source_path),
                            "offset": abs_offset,
                            "size": len(data),
                            "type": key,
                            "temp_path": os.path.abspath(out_path),
                            "created": None,
                            "modified": None,
                            "status": None
                        })
                        print(f"[✓] {filename} @ {abs_offset} ({len(data)} bytes)")
                        start = end

                # Giữ lại phần cuối
                if len(buffer) > MAX_BUFFER:
                    file_offset_base += len(buffer) - MAX_BUFFER
                    buffer = buffer[-MAX_BUFFER:]
                else:
                    file_offset_base += len(chunk)

    except Exception as e:
        print(f"[❌] Lỗi đọc file/ổ đĩa: {e}")

    # Xuất JSON
    output_json = "deleted_files.json"
    if results:
        with open(output_json, "w", encoding="utf-8") as jf:
            json.dump(results, jf, indent=2, ensure_ascii=False)
        print(f"[✅] Đã khôi phục {len(results)} file (kết quả lưu trong {output_json}).")
    else:
        print("[⚠️] Không phát hiện file hợp lệ nào.")


# ▶️ Chạy chương trình
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Cách dùng: python carve_office_extended.py <device_or_image_path> [GB_demo]")
        sys.exit(0)
    drive = sys.argv[1]
    size = float(sys.argv[2]) if len(sys.argv) > 2 else 56.3
    carve_unified(drive, max_scan_gb=size)
