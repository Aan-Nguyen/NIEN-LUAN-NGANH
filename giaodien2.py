from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont, QPixmap, QImage
import sys, json, subprocess, os, datetime, re
from styles import get_app_stylesheet
from config import MENU_ITEMS
from utils import format_size

sys.stdout.reconfigure(encoding='utf-8')

# -------------------- Helpers (Không đổi) --------------------
def read_file_from_image(image_path, offset, size, max_preview=1024*100*100):
    """Đọc dữ liệu từ image/volume theo offset + size, trả về bytes (giới hạn max_preview)."""
    try:
        read_size = min(int(size or 0), max_preview)
        if not image_path:
             print("Lỗi đọc file: image_path là None")
             return b""
        with open(image_path, "rb") as f:
            f.seek(int(offset or 0))
            data = f.read(read_size)
        return data
    except Exception as e:
        print(f"Lỗi đọc file '{image_path}':", e)
        return b""

class NumericItem(QTableWidgetItem):
    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            a = self.data(Qt.UserRole)
            b = other.data(Qt.UserRole)
            if a is not None and b is not None:
                try: return float(a) < float(b)
                except Exception: pass
        return super().__lt__(other)

# -------------------- Scan worker (Không đổi) --------------------
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
                "Size": f.get("size", 0),
                "Ngày tạo": f.get("modified", "") or f.get("created", ""),
                "Tình trạng": f.get("status", ""),
                "Chi tiết": f
            }
            self.file_found.emit(file_info)

        self.finished.emit()

    def stop(self):
        self.running = False


# -------------------- (MỚI) Lớp Panel Chi tiết --------------------
class DetailPreviewPanel(QFrame):
    """Một QWidget độc lập chỉ để quản lý panel bên phải."""
    def __init__(self):
        super().__init__()
        self.setFixedWidth(340)
        self.setObjectName("rightPanel")
        self.setup_panel_ui()

    def setup_panel_ui(self):
        right_layout = QVBoxLayout(self)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(6)

        # Tiêu đề
        title_preview = QLabel("<b>XEM TRƯỚC</b>")
        title_preview.setFixedHeight(25)
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
        right_layout.addWidget(title_detail)

        # Chi tiết
        self.detail_content = QLabel("Chọn file để xem chi tiết.")
        self.detail_content.setWordWrap(True)
        self.detail_content.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        right_layout.addWidget(self.detail_content)

        # Nút khôi phục
        self.recover_btn = QPushButton("💾 Khôi phục file")
        right_layout.addWidget(self.recover_btn)
    
    def update_details(self, chi_tiet):
        """Cập nhật nội dung text chi tiết và lưu chi_tiet vào nút."""
        if not chi_tiet:
            self.detail_content.setText("Không có chi tiết.")
            self.recover_btn.setProperty("current_file", None)
            return
            
        text_lines = []
        for key, value in chi_tiet.items():
            field_name = str(key).replace("_", " ").capitalize()
            if isinstance(value, (list, dict)):
                try: value = json.dumps(value, ensure_ascii=False, indent=2)
                except Exception: value = str(value)
            text_lines.append(f"{field_name}: {value}")
        
        self.detail_content.setText("\n".join(text_lines))
        # Gán chi_tiet vào nút để logic khôi phục có thể truy cập
        self.recover_btn.setProperty("current_file", chi_tiet)

    def update_preview(self, chi_tiet, image_path):
        """Hiển thị preview (ảnh hoặc text)."""
        if not chi_tiet:
            self.preview_label.setText("Không có dữ liệu preview")
            return

        file_type = (chi_tiet.get("type") or "").lower()
        file_name = chi_tiet.get("name", "")
        offset = chi_tiet.get("offset") or chi_tiet.get("start_cluster", 0)
        size = chi_tiet.get("size", 0)

        # ƯU TIÊN: kiểm tra nếu file đã có trong thư mục tạm
        temp_dir = "recovered_files"
        temp_path = os.path.join(temp_dir, file_name)
        if os.path.exists(temp_path):
            try:
                with open(temp_path, "rb") as f:
                    data = f.read()
            except Exception as e:
                print(f"[!] Lỗi đọc tạm: {e}")
                data = b""
        else:
            data = read_file_from_image(image_path, offset, size)

        # Hiển thị hình ảnh
        if file_type in ("jpg", "jpeg", "png", "bmp", "gif", "webp"):
            pix = QPixmap()
            ok = pix.loadFromData(data)
            if ok and not pix.isNull():
                self.preview_label.setPixmap(
                    pix.scaled(
                        self.preview_label.width(),
                        self.preview_label.height(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
            else:
                self.preview_label.setPixmap(QPixmap())
                self.preview_label.setText("Không thể hiển thị preview ảnh (dữ liệu thiếu/không hợp lệ).")
        elif file_type in ("txt", "log", "csv", "json", "xml", "html"):
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = "<Không thể giải mã nội dung>"
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(text[:4000])
        else:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(f"Không hỗ trợ preview cho loại: {file_type}")


# -------------------- (SỬA) Lớp GUI Chính --------------------
class RecoverDeletedApp(QWidget):
    # (MỚI) Định nghĩa tín hiệu
    home_requested = pyqtSignal()
    def __init__(self, target=None, scan_type="quick", session_file=None):
        super().__init__()
        print("[DEBUG] RecoverDeletedApp.__init__() bắt đầu")

        self.session_file = session_file
        self.target_info = target
        self.scan_type = scan_type
        self.deleted_files = []
        self.current_session_file = None

        self.setStyleSheet(get_app_stylesheet())

        # MUST setup UI before loading data
        self.setupUI()

        # Logic khởi động
        if session_file:
            self.load_session(session_file)
        elif self.target_info:
            self.start_scan()
        else:
             self.status_label.setText("Sẵn sàng. (Không có target)")
             
        print("[DEBUG] RecoverDeletedApp.__init__() hoàn tất")

    def setupUI(self):
        """Thiết lập bố cục 3 phần: Sidebar | Nội dung | Chi tiết."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(20)

        # --- 1️⃣ Sidebar bên trái ---
        self.setup_side_bar(main_layout)

        # --- 2️⃣ Khu vực nội dung chính ---
        content_layout = QVBoxLayout()
        content_layout.setSpacing(10)
        self.setup_top_bar(content_layout)
        self.setup_table(content_layout)

        self.status_label = QLabel("Sẵn sàng.")
        content_layout.addWidget(self.status_label)
        main_layout.addLayout(content_layout, stretch=3)

        # --- 3️⃣ Panel chi tiết bên phải ---
        self.detail_panel = DetailPreviewPanel()
        main_layout.addWidget(self.detail_panel, stretch=2)

        # --- Kết nối tín hiệu ---
        self.table.currentCellChanged.connect(self.handle_cell_change)
        self.detail_panel.recover_btn.clicked.connect(self.recover_file)

    def setup_side_bar(self, parent_layout):
        """Tạo thanh sidebar bên trái."""
        side_bar = QVBoxLayout()
        side_bar.setSpacing(20)
        side_bar.setAlignment(Qt.AlignTop)
        side_bar.setContentsMargins(10,20,10,20)

        # Tiêu đề sidebar
        side_bar.addWidget(QLabel("🗂 <b>Scanning</b>", alignment=Qt.AlignCenter, font=QFont("Segoe UI", 14)))
        # Nút Home
        home_btn = QPushButton("🏠 Home")
        home_btn.setFixedHeight(40)
        home_btn.clicked.connect(self.go_home)
        side_bar.addWidget(home_btn)

        # Nút Quét lại
        rescan_btn = QPushButton("🔄 Quét lại")
        home_btn.setFixedHeight(40)
        rescan_btn.clicked.connect(self.start_scan)
        side_bar.addWidget(rescan_btn)

        # Nút Lưu phiên
        save_btn = QPushButton("💾 Lưu phiên")
        home_btn.setFixedHeight(40)
        save_btn.clicked.connect(self.save_session)
        side_bar.addWidget(save_btn)

        # Spacer để nút dính lên trên
        # --- Bọc layout trong QFrame --- 
        side_frame = QFrame() 
        side_frame.setLayout(side_bar) 
        side_frame.setFixedWidth(220) # 👈 Đặt chiều rộng cố định chuẩn 
        side_frame.setObjectName("sidebar") # (tuỳ chọn) để áp CSS riêng # --- Thêm vào layout chính --- 
        parent_layout.addWidget(side_frame)

    def setup_top_bar(self, parent_layout):
        """Hàm helper để tạo top bar (nút + tìm kiếm)."""
        top_bar = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Tìm theo tên file...")
        self.search_box.setFixedWidth(250)
        self.search_box.textChanged.connect(self.filter_table)
        top_bar.addWidget(self.search_box, alignment=Qt.AlignRight)
        
        parent_layout.addLayout(top_bar)

    def setup_table(self, parent_layout):
        """Hàm helper để tạo QTableWidget."""
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Tên", "Loại", "Size", "Ngày tạo", "Tình trạng"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        parent_layout.addWidget(self.table)

    def start_scan(self):
        self.status_label.setText("🔍 Đang quét dữ liệu, vui lòng chờ...")
        self.worker = ScanWorker(self.target_info, self.scan_type)
        self.worker.file_found.connect(self.add_file_to_table)
        self.worker.finished.connect(self.scan_done)
        self.worker.start()

    def add_file_to_table(self, f):
        """Thêm 1 file (đã định dạng) vào bảng."""
        orig_index = len(self.deleted_files)
        self.deleted_files.append(f) # f là dict đã định dạng

        row = self.table.rowCount()
        self.table.insertRow(row)

        # Cột tên (lưu orig_index để mapping sau sort)
        name_item = QTableWidgetItem(f.get("Tên file", ""))
        name_item.setData(Qt.UserRole, orig_index)
        self.table.setItem(row, 0, name_item)

        # Cột loại
        self.table.setItem(row, 1, QTableWidgetItem(f.get("Loại", "")))

        # Cột Size
        raw_size = 0
        chi = f.get("Chi tiết", {}) or {}
        try: raw_size = int(chi.get("size", f.get("Size", 0)) or 0)
        except Exception: raw_size = 0
        size_item = NumericItem(format_size(raw_size))
        size_item.setData(Qt.UserRole, raw_size)
        self.table.setItem(row, 2, size_item)

        # Cột Ngày tạo
        date_str = f.get("Ngày tạo", "") or ""
        date_item = NumericItem(date_str)
        qdt = QDateTime.fromString(date_str, "dd/MM/yyyy HH:mm:ss")
        timestamp = qdt.toSecsSinceEpoch() if qdt.isValid() else 0
        date_item.setData(Qt.UserRole, int(timestamp))
        self.table.setItem(row, 3, date_item)

        # Cột tình trạng
        self.table.setItem(row, 4, QTableWidgetItem(f.get("Tình trạng", "")))

        if row % 100 == 0: # Cập nhật status_label ít thường xuyên hơn
             self.status_label.setText(f"Tìm thấy {len(self.deleted_files)} file bị xóa...")

    def scan_done(self):
        self.table.setSortingEnabled(True)
        self.status_label.setText(f"✅ Hoàn tất - Tổng cộng {len(self.deleted_files)} file bị xóa.")
        QMessageBox.information(self, "Hoàn tất", "Quét file bị xóa hoàn tất!")

    # ---------- (SỬA) Hàm xử lý sự kiện chọn file MỚI ----------
    def handle_cell_change(self, current_row, current_col, prev_row, prev_col):
        """Hàm thống nhất để xử lý khi chọn cell/row mới."""
        if current_row < 0:
            return
        
        name_item = self.table.item(current_row, 0)
        if not name_item:
            return
        
        orig_index = name_item.data(Qt.UserRole)
        if orig_index is None or orig_index >= len(self.deleted_files):
            return
            
        # Lấy dữ liệu
        chi_tiet = self.deleted_files[orig_index].get("Chi tiết", {})
        image_path = self.target_info.get("path") if self.target_info else None

        # Yêu cầu panel bên phải tự cập nhật
        self.detail_panel.update_details(chi_tiet)
        self.detail_panel.update_preview(chi_tiet, image_path)

    # ---------- (LOẠI BỎ) show_file_detail, show_file_detail_by_cell, show_preview ----------
    # Logic của chúng đã được chuyển vào handle_cell_change và DetailPreviewPanel
    
    def recover_file(self):
        """Khôi phục file đã chọn — ưu tiên file tạm khi quét sâu."""
        chi_tiet = self.detail_panel.recover_btn.property("current_file")
        if not chi_tiet:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một file để khôi phục.")
            return

        file_name = chi_tiet.get("name", "recovered_file")
        temp_path = chi_tiet.get("temp_path") or os.path.join("recovered_files", file_name)

        # Hỏi người dùng nơi lưu
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Chọn nơi lưu file khôi phục", file_name
        )
        if not save_path:
            return

        try:
            # ⚙️ Nếu là quét sâu và có file tạm thì chỉ cần copy
            if os.path.exists(temp_path):
                with open(temp_path, "rb") as src, open(save_path, "wb") as dst:
                    dst.write(src.read())
                QMessageBox.information(
                    self, "Hoàn tất",
                    f"File đã được khôi phục (copy từ file tạm):\n{save_path}"
                )
                return

            # 🧠 Nếu không có file tạm (ví dụ quét nhanh) thì đọc từ image
            image_path = self.target_info.get("path")
            offset = chi_tiet.get("offset", 0)
            size = chi_tiet.get("size", 0)
            data = read_file_from_image(image_path, offset, size)

            with open(save_path, "wb") as f:
                f.write(data)
            QMessageBox.information(
                self, "Hoàn tất",
                f"File đã được khôi phục (đọc từ image):\n{save_path}"
            )

        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể khôi phục file:\n{e}")


    def filter_table(self, text):
        """Lọc bảng (Không đổi)."""
        text = text.strip().lower()
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)

    def go_home(self):
        print("[DEBUG] RecoverDeletedApp: phát tín hiệu home_requested")
        self.home_requested.emit()
        temp_dir = "recovered_files"
        if os.path.exists(temp_dir):
            try:
                for file_name in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, file_name)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                print(f"[CLEANUP] Đã xóa tất cả file trong thư mục tạm: {temp_dir}")
            except Exception as e:
                print(f"[LỖI] Không thể xóa thư mục tạm ({temp_dir}): {e}")
    # ---------- Logic Lưu / Tải (Không đổi, giữ nguyên) ----------
    def save_session(self):
        if not self.deleted_files:
            QMessageBox.warning(self, "Lỗi", "Không có dữ liệu file để lưu.")
            return
        device_name = "unknown_device"
        if hasattr(self, "target_info") and self.target_info:
            info = self.target_info
            if "letter" in info or "filesystem" in info:
                device_name = info.get("label") or info.get("letter") or "volume"
            else:
                device_name = info.get("model") or info.get("name") or "disk"
        else:
            QMessageBox.warning(self, "Lỗi", "Không có thông tin target (ổ đĩa) đi kèm. Không thể lưu phiên.")
            return

        device_name = str(device_name)
        device_name = re.sub(r'[\\/:*?"<>|]', '', device_name).strip().replace(' ', '_')
        session_dir = "sessions"
        os.makedirs(session_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        new_session_name = f"session_{device_name}_{timestamp}.json"
        session_file = os.path.join(session_dir, new_session_name)

        session_data_to_save = {
            "target_info": self.target_info,
            "scan_type": self.scan_type,
            "deleted_files_formatted": self.deleted_files
        }
        try:
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session_data_to_save, f, ensure_ascii=False, indent=2)
            self.current_session_file = session_file
            
            index_file = os.path.join(session_dir, "index.json")
            sessions_index = []
            if os.path.exists(index_file):
                with open(index_file, "r", encoding="utf-8") as f:
                    try: sessions_index = json.load(f)
                    except json.JSONDecodeError: sessions_index = []

            session_info = {
                "session_name": f"Phiên {timestamp}",
                "device_name": device_name,
                "timestamp": timestamp,
                "file_path": session_file,
            }
            sessions_index.append(session_info)
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(sessions_index, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Đã lưu", f"Đã tạo phiên làm việc:\n{session_file}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu phiên làm việc:\n{e}")

    def load_session(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)
            print("[DEBUG] Dữ liệu session đã đọc thành công")

            files_to_load = []
            if isinstance(session_data, dict) and "deleted_files_formatted" in session_data:
                print("[DEBUG] Phát hiện định dạng session MỚI.")
                files_to_load = session_data.get("deleted_files_formatted", [])
                loaded_target = session_data.get("target_info")
                if loaded_target:
                    self.target_info = loaded_target 
                self.scan_type = session_data.get("scan_type", "quick")
            elif isinstance(session_data, list):
                print("[DEBUG] Phát hiện định dạng session CŨ. Đang chuyển đổi...")
                QMessageBox.warning(self, "Phiên cũ", "Đây là phiên bản lưu cũ (chỉ chứa dữ liệu thô). Đang cố gắng chuyển đổi...")
                for f_raw in session_data:
                    files_to_load.append({
                        "Tên file": f_raw.get("name", ""),
                        "Loại": f_raw.get("type", ""),
                        "Size": f_raw.get("size", 0),
                        "Ngày tạo": f_raw.get("modified", "") or f_raw.get("created", ""),
                        "Tình trạng": f_raw.get("status", ""),
                        "Chi tiết": f_raw
                    })
            else:
                raise ValueError("Định dạng file session không hợp lệ.")

            print("[DEBUG] --- Bắt đầu load dữ liệu vào table ---")
            self.deleted_files = [] 
            self.table.setSortingEnabled(False)
            self.table.setRowCount(0)
            
            for file_info in files_to_load:
                self.add_file_to_table(file_info)

            self.table.setSortingEnabled(False) 

            status_text = f"📂 Đã tải phiên: {os.path.basename(file_path)} ({len(self.deleted_files)} file)"
            if self.target_info:
                status_text += f" | Target: {self.target_info.get('path', 'N/A')}"
            else:
                status_text += " | (Không rõ target - Chế độ chỉ xem)"
            self.status_label.setText(status_text)
            
            self.current_session_file = file_path
            print("[DEBUG] --- Load session xong ---")
        except Exception as e:
            print(f"[ERROR] Lỗi khi load_session: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể tải phiên:\n{e}")

# -------------------- RUN DEMO (Không đổi) --------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    demo_target = {"label": "Ổ F:", "path": r"\\.\F:", "filesystem": "FAT"}
    w = RecoverDeletedApp(target=demo_target, scan_type="quick")
    w.show()
    sys.exit(app.exec_())