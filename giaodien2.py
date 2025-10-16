# giaodien2.py
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
import sys, os, json
from styles import get_app_stylesheet
from config import MENU_ITEMS
from quet_nhanh import scan_deleted_fat_with_offset  # <-- import hàm quét thật

sys.stdout.reconfigure(encoding='utf-8')



# ================== LUỒNG QUÉT FILE ==================
class ScanWorker(QThread):
    file_found = pyqtSignal(dict)   # Gửi từng file mới tìm thấy
    finished = pyqtSignal()         # Khi quét xong

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
        self.running = True

    def run(self):
        # Gọi hàm quét và emit từng kết quả
        for file_info in scan_deleted_fat_with_offset(self.image_path):
            if not self.running:
                break
            self.file_found.emit(file_info)
        self.finished.emit()

    def stop(self):
        self.running = False


# ================== GIAO DIỆN 2 ==================
class RecoverDeletedApp(QWidget):
    def __init__(self, target=None, scan_type="quick"):
        super().__init__()
        self.setWindowTitle("Recover Deleted Files")
        self.resize(1100, 650)
        self.setStyleSheet(get_app_stylesheet())
        # Lưu thông tin phân vùng/ổ đĩa và kiểu quét
        self.target_info = target
        self.scan_type = scan_type

                # 🧩 In ra thông tin mà giao diện 1 gửi qua để kiểm tra
        print("=== DỮ LIỆU NHẬN TỪ GIAO DIỆN 1 ===")
        print(json.dumps(self.target_info, indent=4, ensure_ascii=False))
        print("Kiểu quét:", self.scan_type)
        print("====================================\n")

        # Lưu thông tin phân vùng/ổ đĩa và kiểu quét
        self.target_info = target
        self.scan_type = scan_type
        self.deleted_files = []  # danh sách file bị xóa

        self.setupUI()

        # Nếu có target thì tự động chạy quét
        if self.target_info:
            image_path = self.target_info.get("")
            if image_path:
                self.start_scan(image_path)

    def setupUI(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)

        # ========== Sidebar ==========
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(20)
        sidebar_layout.setContentsMargins(10,20,10,20)
        sidebar_layout.addWidget(QLabel("🧭 <b>Recover File</b>", alignment=Qt.AlignCenter, font=QFont("Segoe UI",14)))

        menu = QListWidget()
        menu.setFixedWidth(200)
        for name in MENU_ITEMS:
            menu.addItem(QListWidgetItem(name))
        sidebar_layout.addWidget(menu)

        sidebar = QFrame()
        sidebar.setLayout(sidebar_layout)
        sidebar.setFixedWidth(220)
        sidebar.setObjectName("sidebar")

        # ========== Content ==========
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20,20,20,20)

        self.label_target = QLabel("", font=QFont("Segoe UI",13,QFont.Bold))
        content_layout.addWidget(self.label_target)

        # Bảng kết quả
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Tên file", "Loại", "Size", "Ngày tạo", "Tình trạng"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        content_layout.addWidget(self.table)

        # Thanh trạng thái tiến trình
        self.status_label = QLabel("Đang khởi tạo quét...")
        content_layout.addWidget(self.status_label)

        # ========== Right panel ==========
        right_panel = QFrame()
        right_panel.setFixedWidth(260)
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15,15,15,15)
        right_layout.addWidget(QLabel("<b>THÔNG TIN FILE</b>"))

        self.detail_image = QLabel("NO IMAGE", alignment=Qt.AlignCenter)
        self.detail_image.setFixedSize(220,100)
        self.detail_image.setStyleSheet("border:1px solid #ccc; background:#eef1f5; border-radius:5px;")
        right_layout.addWidget(self.detail_image)

        self.detail_info = QLabel("Chọn file để xem chi tiết.")
        self.detail_info.setWordWrap(True)
        right_layout.addWidget(self.detail_info)
        right_layout.addStretch()

        # Gộp layout
        main_layout.addWidget(sidebar)
        main_layout.addLayout(content_layout)
        main_layout.addWidget(right_panel)

        # Kết nối chọn file
        self.table.itemClicked.connect(self.show_file_detail)

        # Cập nhật label nếu có thông tin target
        if self.target_info:
            self.label_target.setText(f"Đang quét: {self.target_info.get('label', self.target_info.get('model',''))} ({self.scan_type})")

    # ================== HÀM QUÉT ==================
    def start_scan(self, image_path):
        self.status_label.setText("🔍 Đang quét dữ liệu, vui lòng chờ...")
        self.worker = ScanWorker(image_path)
        self.worker.file_found.connect(self.add_file_to_table)
        self.worker.finished.connect(self.scan_done)
        self.worker.start()

    def add_file_to_table(self, f):
        """Nhận dữ liệu từ worker và hiển thị ngay"""
        self.deleted_files.append(f)
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(f["full_path"]))
        self.table.setItem(row, 1, QTableWidgetItem(f["type"]))
        self.table.setItem(row, 2, QTableWidgetItem(str(f["size"])))
        self.table.setItem(row, 3, QTableWidgetItem(f["ctime"]))
        self.table.setItem(row, 4, QTableWidgetItem(f["status"]))
        self.status_label.setText(f"Tìm thấy {len(self.deleted_files)} file bị xóa...")

    def scan_done(self):
        """Khi quét hoàn tất"""
        self.status_label.setText(f"✅ Hoàn tất - Tổng cộng {len(self.deleted_files)} file bị xóa.")
        QMessageBox.information(self, "Hoàn tất", "Quét file bị xóa hoàn tất!")

    # ================== CHI TIẾT FILE ==================
    def show_file_detail(self, item):
        row = item.row()
        if row < 0 or row >= len(self.deleted_files):
            return
        f = self.deleted_files[row]
        self.detail_info.setText(
            f"<b>Tên file:</b> {f.get('full_path','')}<br>"
            f"<b>Kích thước:</b> {f.get('size','0')} bytes<br>"
            f"<b>Cluster bắt đầu:</b> {f.get('start_cluster','?')}<br>"
            f"<b>Offset:</b> {f.get('offset_bytes','?')}<br>"
            f"<b>Tình trạng:</b> {f.get('status','Unknown')}"
        )
        self.detail_image.setText("NO IMAGE")
        self.detail_image.setPixmap(QPixmap())


# ================== DEMO CHẠY RIÊNG ==================
if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    demo_target = {"label": "Ổ E:", "path": r"\\.\E:"}
    w = RecoverDeletedApp(target=demo_target, scan_type="quick")
    w.show()
    sys.exit(app.exec_())
