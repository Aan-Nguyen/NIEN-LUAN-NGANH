# config.py

import os

# --- CẤU HÌNH ĐƯỜNG DẪN DỮ LIỆU ---
# Thay thế bằng đường dẫn thực tế của bạn
JSON_PATH = r"C:\NLN\code\Machine-Learning-Forensic-Application\disk_info.json"
# --- TIÊU ĐỀ BẢNG VÀ MENU ---
TREE_HEADERS = ["Tên thiết bị / Phân vùng", "Loại", "Kết nối / FS", "Dung lượng"]
MENU_ITEMS = ["🏠  Home", "🔍  Quét dữ liệu", "📋  Phiên làm việc"]

# --- ĐƯỜNG DẪN ẢNH GIẢ LẬP (Tùy thuộc cấu trúc thư mục của bạn) ---
IMAGE_PATH_INTERNAL = "gui/assets/logo.png"
IMAGE_PATH_USB = "gui/assets/icons/usb_drive.png"
IMAGE_PATH_PARTITION = "gui/assets/icons/partition.png"