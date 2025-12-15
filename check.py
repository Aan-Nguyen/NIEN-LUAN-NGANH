#!/usr/bin/env python3
"""
UNIVERSAL FORENSIC INTEGRITY ANALYZER (HYBRID MEMORY/DISK)
Chức năng:
  - Hỗ trợ input là Đường dẫn file (cho Quét Sâu) HOẶC Bytes thô (cho Quét Nhanh).
  - Giữ nguyên toàn bộ logic phân tích Visual/Structure/Office/PDF mạnh nhất.
"""

import os
import struct
import math
import zipfile
import io
from collections import Counter
import argparse
import sys

# Import PIL
try:
    from PIL import Image, ImageFile, ImageStat
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    print("Warning: Pillow not found. Visual check disabled.")

# ==========================================
# 1. SMART INPUT HANDLER (XỬ LÝ ĐẦU VÀO)
# ==========================================
def get_data_and_size(source):
    if isinstance(source, str): 
        if not os.path.exists(source): return b"", 0
        try:
            with open(source, "rb") as f:
                data = f.read()
            return data, len(data)
        except: return b"", 0
    elif isinstance(source, bytes):
        return source, len(source)
    return b"", 0

# ==========================================
# 2. SHARED UTILITIES
# ==========================================
def calculate_entropy_and_zeros(data):
    file_size = len(data)
    if file_size == 0: return 0, 0
    
    zero_count = data.count(b'\x00')
    zero_ratio = (zero_count / file_size) * 100.0

    if file_size > 5 * 1024 * 1024: 
        step = file_size // 5000
        sample = data[::step]
    else:
        sample = data

    counts = Counter(sample)
    ent = 0.0
    total = len(sample)
    for c in counts.values():
        p = c / total
        ent -= p * math.log2(p)
    
    return ent, zero_ratio

# ==========================================
# 3. IMAGE ANALYSIS
# ==========================================
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SOI = b"\xff\xd8"
WEBP_RIFF = b"RIFF"
WEBP_WEBP = b"WEBP"

def analyze_visual_pixel(data):
    if not HAS_PILLOW: return 0.0
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        if img.mode != 'RGB': img = img.convert("RGB")
        w, h = img.size
        
        step = max(1, h // 50)
        corrupted_rows = 0
        
        for y in range(h - step, 0, -step):
            region = img.crop((0, y, w, y + step))
            stat = ImageStat.Stat(region)
            variance = sum(stat.var) / 3
            if variance < 2.0: 
                corrupted_rows += step
            else:
                break 
        
        return min(100.0, (corrupted_rows / h) * 100.0)
    except:
        return 100.0

def analyze_image_structure(data, ftype):
    file_size = len(data)
    corrupted_bytes = 0
    missing_tail = False

    if ftype == "PNG":
        if not data.startswith(PNG_SIGNATURE): return 100.0
        pos = len(PNG_SIGNATURE)
        while pos < len(data):
            if pos + 8 > len(data): break
            try:
                length = struct.unpack(">I", data[pos:pos+4])[0]
                if length > file_size: 
                    corrupted_bytes += (file_size - pos)
                    break
                pos += length + 12
            except: break
        if b'IEND' not in data[-20:]: missing_tail = True

    elif ftype == "JPEG":
        if not data.startswith(JPEG_SOI): return 100.0
        if not data.rstrip(b'\x00').endswith(b'\xff\xd9'): missing_tail = True

    elif ftype == "WEBP":
        if not (data.startswith(WEBP_RIFF) and data[8:12] == WEBP_WEBP): return 100.0
        try:
            riff_len = struct.unpack("<I", data[4:8])[0]
            if riff_len + 8 > file_size:
                missing_tail = True
                corrupted_bytes = (riff_len + 8) - file_size
        except: missing_tail = True

    raw_damage = corrupted_bytes
    if missing_tail: raw_damage += 1024
    
    struct_pct = (raw_damage / file_size) * 100.0 if file_size > 0 else 0
    return min(100.0, struct_pct)

def get_image_integrity(data, img_type):
    vis_damage = analyze_visual_pixel(data)
    struct_damage = analyze_image_structure(data, img_type)
    
    final_damage = max(vis_damage, struct_damage)
    if vis_damage < 1.0 and struct_damage > 0 and struct_damage < 20:
        final_damage = min(final_damage, 5.0)

    ent, _ = calculate_entropy_and_zeros(data)
    if ent < 1.0: final_damage = 100.0

    return 100.0 - final_damage

# ==========================================
# 4. DOCUMENT ANALYSIS
# ==========================================
def analyze_office_integrity(data):
    if not data.startswith(b"PK\x03\x04"): return 0.0
    try:
        with zipfile.ZipFile(io.BytesIO(data), 'r') as zf:
            if zf.testzip(): return 50.0
            infolist = zf.infolist()
            if not infolist: return 0.0
            
            filenames = [f.filename for f in infolist]
            if not any(x in filenames for x in ['[Content_Types].xml', '_rels/.rels']):
                return 20.0
            return 100.0
    except: return 0.0

def analyze_pdf_integrity(data):
    if not data.startswith(b"%PDF-"): return 0.0
    
    tail = data[-1024:] if len(data) > 1024 else data
    has_eof = b'%%EOF' in tail
    ent, zero_ratio = calculate_entropy_and_zeros(data)
    
    score = 100.0
    if not has_eof: score -= 20.0
    if zero_ratio > 10.0: score -= zero_ratio
    if ent < 4.0: score = 0.0
        
    return max(0.0, score)

# ==========================================
# 5. MAIN DISPATCHER
# ==========================================
def analyze_file_integrity(source, ext=None):
    """
    Trả về:
      - float (0.0 - 100.0): Nếu file thuộc loại hỗ trợ (Ảnh/Office/PDF)
      - None: Nếu file không hỗ trợ hoặc rỗng
    """
    data, size = get_data_and_size(source)
    if size == 0: return None # File rỗng hoặc không đọc được
    
    if ext is None and isinstance(source, str):
        ext = os.path.splitext(source)[1]
    
    if not ext: return None
    ext = ext.lower().replace(".", "")

    # --- ROUTING ---
    img_type = None
    if ext in ['png']: img_type = "PNG"
    elif ext in ['jpg', 'jpeg']: img_type = "JPEG"
    elif ext in ['webp']: img_type = "WEBP"
    
    if img_type:
        return get_image_integrity(data, img_type)
    
    if ext in ['docx', 'xlsx', 'pptx', 'odt', 'ods', 'odp']:
        return analyze_office_integrity(data)
    
    if ext == 'pdf':
        return analyze_pdf_integrity(data)
    
    # === [THAY ĐỔI] ===
    # File lạ -> Trả về None để báo hiệu "Không biết check"
    return None

# Hàm Alias
check_file = analyze_file_integrity

# ==========================================
# 6. CLI
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", required=True, help="File path")
    args = parser.parse_args()
    
    try:
        score = analyze_file_integrity(args.file)
        if score is not None:
            print(f"{score:.2f}")
        else:
            print("N/A") # Not Applicable
    except Exception:
        print("Error")