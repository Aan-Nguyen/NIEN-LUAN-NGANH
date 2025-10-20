# giaodien2.py
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont, QPixmap, QImage
import sys, json, subprocess, os
from styles import get_app_stylesheet
from config import MENU_ITEMS

sys.stdout.reconfigure(encoding='utf-8')

# -------------------- Helpers --------------------
def read_file_from_image(image_path, offset, size, max_preview=1024*100*100):
    """Đọc dữ liệu từ image/volume theo offset + size, trả về bytes (giới hạn max_preview)."""
    try:
        read_size = min(int(size or 0), max_preview)
        with open(image_path, "rb") as f:
            f.seek(int(offset or 0))
            data = f.read(read_size)
        return data
    except Exception as e:
        print("Lỗi đọc file:", e)
        return b""

def format_size(size_bytes):
    """Chuyển byte -> KB/MB/GB (chuỗi hiển thị)."""
    try:
        if size_bytes is None:
            return "0 B"
        size = float(size_bytes)
    except Exception:
        return "0 B"
    if size < 1024:
        return f"{size:.0f} B"
    elif size < 1024**2:
        return f"{size/1024:.2f} KB"
    elif size < 1024**3:
        return f"{size/1024**2:.2f} MB"
    else:
        return f"{size/1024**3:.2f} GB"



# Custom item để sort theo Qt.UserRole (số thực), nhưng vẫn hiển thị text
class NumericItem(QTableWidgetItem):
    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            a = self.data(Qt.UserRole)
            b = other.data(Qt.UserRole)
            if a is not None and b is not None:
                try:
                    return float(a) < float(b)
                except Exception:
                    pass
        return super().__lt__(other)

# -------------------- Scan worker --------------------
class ScanWorker(QThread):
    file_found = pyqtSignal(dict)
    finished = pyqtSignal()

    def __init__(self, target_info, scan_type="quick"):
        super().__init__()
        self.target_info = target_info
        self.scan_type = scan_type
        self.running = True

    def run(self):
        image_path = self.target_info.get("path")
        fs_type = self.target_info.get("filesystem", "").upper()
        if not image_path:
            self.finished.emit()
            return

        try:
            if self.scan_type == "quick":
                if fs_type in ["FAT", "FAT32", "EXFAT"]:
                    subprocess.run([sys.executable, "quet_nhanh_fat.py", image_path], check=True)
                elif fs_type == "NTFS":
                    subprocess.run([sys.executable, "quet_nhanh_ntfs.py", image_path], check=True)
                else:
                    print("Filesystem không hỗ trợ quét nhanh.")
                    self.finished.emit()
                    return
            else:
                # quet_sau.py nên tạo deleted_files.json
                subprocess.run([sys.executable, "quet_sau.py", image_path], check=True)
        except Exception as e:
            print("Lỗi khi quét:", e)
            self.finished.emit()
            return

        result_json = "deleted_files.json"
        if not os.path.exists(result_json):
            print(f"Không tìm thấy file {result_json}")
            self.finished.emit()
            return

        try:
            with open(result_json, "r", encoding="utf-8") as fh:
                all_files = json.load(fh)
        except Exception as e:
            print("Lỗi đọc JSON:", e)
            self.finished.emit()
            return

        for f in all_files:
            if not self.running:
                break
            file_info = {
                "Tên file": f.get("name", ""),
                "Loại": f.get("type", ""),
                # giữ size thực (số) trong Chi tiết, nhưng cung cấp trường Size hiển thị sau
                "Size": f.get("size", 0),
                "Ngày tạo": f.get("modified", "") or f.get("created", ""),
                "Tình trạng": f.get("status", ""),
                "Chi tiết": f
            }
            self.file_found.emit(file_info)

        self.finished.emit()

    def stop(self):
        self.running = False

# -------------------- GUI --------------------
class RecoverDeletedApp(QWidget):
    def __init__(self, target=None, scan_type="quick"):
        super().__init__()
        self.setWindowTitle("Recover Deleted Files")
        self.resize(1150, 650)
        self.setStyleSheet(get_app_stylesheet())

        self.target_info = target
        self.scan_type = scan_type
        self.deleted_files = []

        self.setupUI()

        if self.target_info:
            self.start_scan()

    def setupUI(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(20)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.addWidget(QLabel("🧭 <b>Recover File</b>", alignment=Qt.AlignCenter, font=QFont("Segoe UI", 14)))

        menu = QListWidget()
        menu.setFixedWidth(200)
        for name in MENU_ITEMS:
            menu.addItem(QListWidgetItem(name))
        sidebar_layout.addWidget(menu)

        home_btn = QPushButton("🏠 Home")
        home_btn.clicked.connect(self.go_home)
        sidebar_layout.addWidget(home_btn)

        sidebar = QFrame()
        sidebar.setLayout(sidebar_layout)
        sidebar.setFixedWidth(220)
        sidebar.setObjectName("sidebar")

        # Content (middle)
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)

        # --- Thanh tiêu đề + ô tìm kiếm ---
        top_bar = QHBoxLayout()

        self.label_target = QLabel("", font=QFont("Segoe UI", 13, QFont.Bold))
        top_bar.addWidget(self.label_target, stretch=1)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Tìm theo tên file...")
        self.search_box.setFixedWidth(250)
        self.search_box.textChanged.connect(self.filter_table)
        top_bar.addWidget(self.search_box)

        content_layout.addLayout(top_bar)


        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Tên", "Loại", "Size", "Ngày tạo", "Tình trạng"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # không bật sorting ngay ở đây, sẽ bật sau khi có dữ liệu để tránh 1 số edge-case
        content_layout.addWidget(self.table)

        self.status_label = QLabel("Đang khởi tạo quét...")
        content_layout.addWidget(self.status_label)

        # Right panel (preview trên + detail dưới)
        right_panel = QFrame()
        right_panel.setFixedWidth(340)
        right_panel.setObjectName("rightPanel")

        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(6)

        # Tiêu đề
        title_preview = QLabel("<b>XEM TRƯỚC</b>")
        title_preview.setFixedHeight(25)
        title_preview.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        right_layout.addWidget(title_preview)

        # Preview image
        self.preview_label = QLabel("Chọn file để xem preview")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(300, 180)
        self.preview_label.setStyleSheet("border:1px solid #ccc; background:#fafafa; border-radius:4px;")
        right_layout.addWidget(self.preview_label)

        # Tiêu đề 2
        title_detail = QLabel("<b>CHI TIẾT FILE</b>")
        title_detail.setFixedHeight(25)
        title_detail.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        right_layout.addWidget(title_detail)

        # Chi tiết
        self.detail_content = QLabel("Chọn file để xem chi tiết.")
        self.detail_content.setWordWrap(True)
        self.detail_content.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        right_layout.addWidget(self.detail_content)


        # Nút khôi phục
        self.recover_btn = QPushButton("💾 Khôi phục file")
        self.recover_btn.setEnabled(True)  # tắt mặc định, bật khi chọn file
        self.recover_btn.clicked.connect(self.recover_file)
        right_layout.addWidget(self.recover_btn)
        
        main_layout.addWidget(sidebar)
        main_layout.addLayout(content_layout)
        main_layout.addWidget(right_panel)

        self.table.itemClicked.connect(self.show_file_detail)

        if self.target_info:
            self.label_target.setText(
                f"Đang quét: {self.target_info.get('label', self.target_info.get('model', ''))} ({self.scan_type})"
            )

    def go_home(self):
        from giaodien1 import RecoverApp
        self.home_window = RecoverApp()
        self.home_window.show()
        self.close()

    def start_scan(self):
        self.status_label.setText("🔍 Đang quét dữ liệu, vui lòng chờ...")
        self.worker = ScanWorker(self.target_info, self.scan_type)
        self.worker.file_found.connect(self.add_file_to_table)
        self.worker.finished.connect(self.scan_done)
        self.worker.start()

    def add_file_to_table(self, f):
        # Lưu index gốc vào deleted_files
        orig_index = len(self.deleted_files)
        self.deleted_files.append(f)

        row = self.table.rowCount()
        self.table.insertRow(row)

        # Cột tên (lưu orig_index để mapping sau sort)
        name_item = QTableWidgetItem(f.get("Tên file", ""))
        name_item.setData(Qt.UserRole, orig_index)
        self.table.setItem(row, 0, name_item)

        # Cột loại
        self.table.setItem(row, 1, QTableWidgetItem(f.get("Loại", "")))

        # Cột Size: hiển thị đẹp, sort theo raw bytes
        raw_size = 0
        chi = f.get("Chi tiết", {}) or {}
        # JSON có thể chứa size ở nhiều key; ưu tiên 'size' numeric
        try:
            raw_size = int(chi.get("size", f.get("Size", 0)) or 0)
        except Exception:
            raw_size = 0
        size_item = NumericItem(format_size(raw_size))
        size_item.setData(Qt.UserRole, raw_size)
        self.table.setItem(row, 2, size_item)

        # Cột Ngày tạo: hiển thị chuỗi, sort theo timestamp
        date_str = f.get("Ngày tạo", "") or ""
        date_item = NumericItem(date_str)
        # thử parse bằng QDateTime (định dạng dd/MM/yyyy HH:mm:ss)
        qdt = QDateTime.fromString(date_str, "dd/MM/yyyy HH:mm:ss")
        timestamp = qdt.toSecsSinceEpoch() if qdt.isValid() else 0
        # fallback: thử vài định dạng Python nếu cần (đã để 0 nếu fail)
        date_item.setData(Qt.UserRole, int(timestamp))
        self.table.setItem(row, 3, date_item)

        # Cột tình trạng
        self.table.setItem(row, 4, QTableWidgetItem(f.get("Tình trạng", "")))

        self.status_label.setText(f"Tìm thấy {len(self.deleted_files)} file bị xóa...")

    def scan_done(self):
        # bật sort sau khi đã điền dữ liệu
        self.table.setSortingEnabled(True)
        self.status_label.setText(f"✅ Hoàn tất - Tổng cộng {len(self.deleted_files)} file bị xóa.")
        QMessageBox.information(self, "Hoàn tất", "Quét file bị xóa hoàn tất!")

    # ---------- Preview when selected ----------
    def show_preview(self, chi_tiet):
        """Hiển thị preview trên preview_label (ảnh hoặc text)."""
        if not chi_tiet:
            self.preview_label.setText("Không có dữ liệu preview")
            return

        file_type = (chi_tiet.get("type") or "").lower()
        offset = chi_tiet.get("offset") or chi_tiet.get("start_cluster", 0)
        # nếu offset lấy từ start_cluster, không đổi (ứng dụng của bạn chuyển start_cluster->offset trước khi lưu)
        size = chi_tiet.get("size", 0)
        image_path = self.target_info.get("path") if self.target_info else None

        if not image_path or not os.path.exists(image_path):
            # Nếu image_path là device path like \\.\F: thì os.path.exists trả False trên Windows,
            # nhưng open sẽ vẫn hoạt động nếu chạy với quyền admin.
            # Ở đây chỉ báo thông báo nếu file image không hợp lệ dạng file hệ thống.
            # Tiếp tục cố đọc và bắt lỗi nếu open thất bại.
            pass

        data = read_file_from_image(image_path, offset, size)

        # Hình ảnh
        if file_type in ("jpg", "jpeg", "png", "bmp", "gif", "webp"):
            pix = QPixmap()
            ok = pix.loadFromData(data)
            if ok and not pix.isNull():
                self.preview_label.setPixmap(pix.scaled(self.preview_label.width(), self.preview_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                # không load được ảnh (dữ liệu có thể bị cắt) -> hiển thị text thông báo
                self.preview_label.setPixmap(QPixmap())
                self.preview_label.setText("Không thể hiển thị preview ảnh (dữ liệu thiếu/không hợp lệ).")
        # Text preview
        elif file_type in ("txt", "log", "csv", "json", "xml", "html"):
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = "<Không thể giải mã nội dung>"
            # show first N chars
            preview_text = text[:4000]
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(preview_text)
        else:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(f"Không hỗ trợ preview cho loại: {file_type}")

    # ---------- Show detail (called on item click) ----------
    def show_file_detail(self, item):
        row = item.row()
        if row < 0:
            return

        name_item = self.table.item(row, 0)
        orig_index = name_item.data(Qt.UserRole) if name_item else row
        if orig_index < 0 or orig_index >= len(self.deleted_files):
            return

        chi_tiet = self.deleted_files[orig_index].get("Chi tiết", {}) or {}
        self.show_preview(chi_tiet)
        self.recover_btn.setProperty("current_file", chi_tiet)

        text_lines = []
        for key, value in chi_tiet.items():
            field_name = str(key).replace("_", " ").capitalize()
            if isinstance(value, (list, dict)):
                try:
                    value = json.dumps(value, ensure_ascii=False, indent=2)
                except Exception:
                    value = str(value)
            text_lines.append(f"{field_name}: {value}")

        self.detail_content.setText("\n".join(text_lines))

    def recover_file(self):
        chi_tiet = self.recover_btn.property("current_file")
        if not chi_tiet:
            return

        default_name = chi_tiet.get("name", "recovered_file")
        file_type = chi_tiet.get("type", "")
        suggested_name = f"{default_name}" if not file_type else f"{default_name}.{file_type}"

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Chọn nơi lưu file khôi phục", suggested_name
        )
        if not save_path:
            return

        image_path = self.target_info.get("path")
        offset = chi_tiet.get("offset", 0)
        size = chi_tiet.get("size", 0)
        data = read_file_from_image(image_path, offset, size)

        try:
            with open(save_path, "wb") as f:
                f.write(data)
            QMessageBox.information(self, "Hoàn tất", f"File đã được khôi phục tại:\n{save_path}")
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể khôi phục file:\n{e}")
    def filter_table(self, text):
        """Lọc bảng theo tất cả các cột."""
        text = text.strip().lower()

        for row in range(self.table.rowCount()):
            match = False  # Biến cờ kiểm tra có ô nào khớp không

            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text().lower():
                    match = True
                    break  # Nếu khớp 1 ô rồi thì không cần kiểm tra cột khác

            self.table.setRowHidden(row, not match)


# -------------------- RUN DEMO --------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    demo_target = {"label": "Ổ F:", "path": r"\\.\F:", "filesystem": "FAT"}
    w = RecoverDeletedApp(target=demo_target, scan_type="quick")
    w.show()
    sys.exit(app.exec_())
