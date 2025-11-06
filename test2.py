import os
from PIL import Image
from io import BytesIO

def show_preview(image_path, offset, size, file_type):
    try:
        filesize = os.path.getsize(image_path)
        print(f"[i] File size: {filesize:,} bytes")
        print(f"[i] Offset: {offset:,} | Size: {size:,}")

        if offset < 0 or offset >= filesize:
            print(f"[⚠️] Offset vượt kích thước file! ({offset} / {filesize})")
            return
        if offset + size > filesize:
            print(f"[⚠️] Phần đọc vượt giới hạn file, sẽ tự cắt lại.")
            size = filesize - offset

        with open(image_path, "rb") as f:
            f.seek(offset)
            data = f.read(size)
    except Exception as e:
        print(f"[!] Lỗi đọc: {e}")
        return

    # ✅ Preview hình ảnh
    if file_type.lower() in ("jpg", "jpeg", "png", "bmp", "gif", "webp"):
        try:
            img = Image.open(BytesIO(data))
            img.show()
            print(f"[✓] Hiển thị ảnh {file_type.upper()} từ offset {offset}")
        except Exception as e:
            print(f"[x] Không thể hiển thị ảnh: {e}")

    # ✅ Preview văn bản
    elif file_type.lower() in ("txt", "log", "csv", "json", "xml", "html"):
        try:
            text = data.decode("utf-8", errors="ignore")
            print("======[ PREVIEW TEXT ]======")
            print(text[:2000])
            print("============================")
        except Exception as e:
            print(f"[x] Không thể đọc text: {e}")
    else:
        print(f"[i] Không hỗ trợ preview cho loại: {file_type}")



# ==============================
# ▶️ Ví dụ test:
# ==============================
if __name__ == "__main__":
    IMAGE_PATH = r"\\.\PhysicalDrive1"   # thay bằng ổ hoặc image thật
    OFFSET = 544427055               # ví dụ offset vật lý
    SIZE = 29246                  # ví dụ kích thước file
    FILE_TYPE = "jpg"              # ví dụ loại file

    show_preview(IMAGE_PATH, OFFSET, SIZE, FILE_TYPE)
