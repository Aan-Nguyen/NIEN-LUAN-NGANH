# giaodien2.py (Đã tối ưu hóa logic sắp xếp và Thêm Khôi phục Tất cả) 
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, 
    QFrame, QTableWidget, QHeaderView, QMessageBox, QLineEdit,
    QTableWidgetItem, QAbstractItemView, QFileDialog, QGraphicsDropShadowEffect, QScrollArea,
    QApplication, QDialog, QProgressBar, QMainWindow, QDockWidget # <-- THÊM MỚI
)
from PyQt5.QtWidgets import QStackedWidget, QTextEdit
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont, QPixmap, QImage, QColor
from dashboard import DashboardWidget
import sys, json, subprocess, os, datetime, re
from styles import get_app_stylesheet
from config import MENU_ITEMS
from utils import format_size # Giả định format_size, NumericItem được import từ utils
import logging # <-- Import thư viện logging

# --- CẤU HÌNH GHI LOG (Thêm đoạn này vào) ---
# Log sẽ được lưu vào file 'activity_log.txt' cùng thư mục
logging.basicConfig(
    filename='activity_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8' 
)

def log_action(message, level="info"):
    """Hàm ghi log hỗ trợ"""
    if level == "info": logging.info(message)
    elif level == "error": logging.error(message)
    elif level == "warning": logging.warning(message)
    print(f"[{level.upper()}] {message}") # Vẫn in ra màn hình console để debug
# (Giữ nguyên DropShadowEffect và NumericItem)
class DropShadowEffect(QGraphicsDropShadowEffect):
    def __init__(self, color=QColor(0, 0, 0, 80), blur_radius=15, x_offset=0, y_offset=6):
        super().__init__()
        self.setBlurRadius(blur_radius)
        self.setColor(color)
        self.setOffset(x_offset, y_offset)

class NumericItem(QTableWidgetItem):
    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            a = self.data(Qt.UserRole)
            b = other.data(Qt.UserRole)
            if a is not None and b is not None:
                try: return float(a) < float(b)
                except Exception: pass
        return super().__lt__(other)
# (Giữ nguyên Helpers và ScanWorker)
def read_file_from_image(image_path, offset, size, max_preview=1024*100*100):
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

def get_best_offset(chi_tiet):
    """
    Ưu tiên offset (Deep Scan).
    Fallback sang start_cluster (Quick Scan).
    """
    if not chi_tiet:
        return 0

    offset = chi_tiet.get("offset")
    if offset is not None:
        try:
            return int(offset)
        except Exception:
            pass

    cluster = chi_tiet.get("start_cluster")
    if cluster is not None:
        try:
            return int(cluster)
        except Exception:
            pass

    return 0

class ScanWorker(QThread):
    file_found = pyqtSignal(dict)
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, target_info, scan_type="quick"):
        super().__init__()
        self.target_info = target_info
        self.scan_type = scan_type
        self.running = True
        self.process = None 

    def run(self):
        image_path = self.target_info.get("path")
        fs_type = self.target_info.get("filesystem", "").upper()
        log_action(f"Bắt đầu quét: {self.scan_type.upper()} trên {image_path} ({fs_type})")
        # 1. Lấy đường dẫn tuyệt đối của thư mục chứa file giaodien2.py
        base_dir = os.path.dirname(os.path.abspath(__file__))

        if not image_path:
            self.finished.emit()
            return
        
        command = []
        script_path = ""

        try:
            # 2. Xây dựng đường dẫn tuyệt đối tới script con
            if self.scan_type == "quick":
                if fs_type in ["FAT", "FAT32", "EXFAT"]:
                    script_path = os.path.join(base_dir, "quet_nhanh_fat.py")
                elif fs_type == "NTFS":
                    script_path = os.path.join(base_dir, "quet_nhanh_ntfs.py")
                else:
                    print("Filesystem không hỗ trợ quét nhanh.")
                    self.finished.emit()
                    return
            else:
                # Quét sâu
                script_path = os.path.join(base_dir, "quet_sau.py")

            # Kiểm tra script có tồn tại không
            if not os.path.exists(script_path):
                print(f"[LỖI] Không tìm thấy script tại: {script_path}")
                self.finished.emit()
                return

            command = [sys.executable, script_path, image_path]
            print(f"[INFO] Running: {command}")

            # 3. Chạy subprocess với cwd=base_dir (QUAN TRỌNG)
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
                text=True,
                encoding='utf-8', 
                errors='replace',  # <--- THÊM DÒNG NÀY (Quan trọng nhất)
                cwd=base_dir
            )

            # Đọc log realtime
            for line in self.process.stdout:
                if not line: continue
                text = line.strip()
                
                # Debug log ra console để bạn thấy script con đang làm gì
                # print(f"[SUB] {text}") 

                if text.startswith("PROGRESS"):
                    parts = text.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        self.progress.emit(int(parts[1]))

            self.process.wait()

            if not self.running:
                print("Quá trình quét bị dừng bởi người dùng.")
                self.finished.emit()
                return

        except Exception as e:
            log_action(f"Lỗi quá trình quét (ScanWorker): {e}", "error")
            print("Lỗi khi chạy subprocess:", e)
            self.finished.emit()
            return
        
        # 4. Đọc file JSON kết quả bằng đường dẫn tuyệt đối
        result_json = os.path.join(base_dir, "deleted_files.json")
        
        if not os.path.exists(result_json):
            print(f"[LỖI] Script chạy xong nhưng không thấy file: {result_json}")
            # Gợi ý: Kiểm tra xem quet_sau.py có lệnh ghi file json không
            self.finished.emit()
            return
        
        try:
            with open(result_json, "r", encoding="utf-8") as f:
                all_files = json.load(f)
        except Exception as e:
            print("Lỗi đọc JSON:", e)
            self.finished.emit()
            return

        # Emit dữ liệu
        for f in all_files:
            if not self.running: break
            
            # Chuẩn hóa dữ liệu phòng trường hợp thiếu trường
            file_info = {
                "Tên file": f.get("name", "Unknown"),
                "Loại": f.get("type", "Unknown"),
                "Size": f.get("size", 0),
                "Ngày tạo": f.get("modified", "") or f.get("created", ""),
                "Tình trạng": f.get("status", ""),
                "Chi tiết": f
            }
            self.file_found.emit(file_info)
        log_action(f"Quá trình quét hoàn tất. Tìm thấy {len(all_files)} file.") # <--- Thêm dòng này
        self.finished.emit()

    def stop(self):
        self.running = False
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                print("[STOP] Đã gửi tín hiệu terminate.")
            except Exception as e:
                print(f"[LỖI] Không thể terminate process: {e}")
                           
# --- DÁN ĐOẠN NÀY VÀO TRƯỚC CLASS CHÍNH ---
class ScanProgressWindow(QDialog):
    stop_requested = pyqtSignal() # Tín hiệu báo dừng

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Đang quét dữ liệu...")
        
        # --- [SỬA 1] Dùng resize thay vì setFixedSize ---
        # Để nút Phóng to hoạt động, cửa sổ phải co giãn được
        self.resize(400, 150) 
        self.setMinimumWidth(300) # Đặt chiều rộng tối thiểu để không bị quá bé
        
        self.setObjectName("ScanProgressWindow") 
        
        # --- [SỬA 2] Thêm nút Phóng to (Maximize) ---
        self.setWindowFlags(
            Qt.Window | 
            Qt.WindowMinimizeButtonHint | 
            Qt.WindowMaximizeButtonHint | # <--- Thêm dòng này
            Qt.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.lbl_status = QLabel("Đang khởi tạo...")
        self.lbl_status.setFont(QFont("Segoe UI", 10))
        self.lbl_status.setObjectName("progressStatusLabel") 
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(25)
        self.progress_bar.setObjectName("scanProgressBar")
        layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_stop = QPushButton("Dừng Quét")
        self.btn_stop.setFixedSize(100, 30)
        self.btn_stop.setObjectName("btnStopScan")
        
        self.btn_stop.clicked.connect(self.on_stop_clicked)
        btn_layout.addWidget(self.btn_stop)
        
        layout.addLayout(btn_layout)

    def update_progress(self, val):
        self.progress_bar.setValue(val)
        self.lbl_status.setText(f"Đang xử lý... {val}%")

    def on_stop_clicked(self):
        self.lbl_status.setText("Đang dừng...")
        self.btn_stop.setEnabled(False)
        self.stop_requested.emit() 
    
    def closeEvent(self, event):
        if self.btn_stop.isEnabled(): 
            self.on_stop_clicked()
        event.accept()# Gửi tín hiệu dừng về Main App

# (Giữ nguyên DetailPreviewPanel)
class DetailPreviewPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(340)
        self.setObjectName("rightPanel")
        self.setGraphicsEffect(DropShadowEffect(blur_radius=15, y_offset=8, color=QColor(0, 0, 0, 30)))
        self.setup_panel_ui()

    def setup_panel_ui(self):
        right_layout = QVBoxLayout(self)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(6)
        title_preview = QLabel("<b>XEM TRƯỚC</b>")
        title_preview.setFixedHeight(25)
        right_layout.addWidget(title_preview)
        preview_container = QFrame()
        preview_container.setObjectName("previewContainer")
        preview_container.setStyleSheet("border: 1px solid #e0e0e0; background: #ffffff; border-radius: 4px;")
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(5, 5, 5, 5)

        self.preview_label = QLabel("Chọn file để xem preview")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(290, 170)
        self.preview_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_label)
        right_layout.addWidget(preview_container)

        title_detail = QLabel("<b>CHI TIẾT FILE</b>")
        title_detail.setFixedHeight(25)
        right_layout.addWidget(title_detail)

        self.detail_content = QLabel("Chọn file để xem chi tiết.")
        self.detail_content.setWordWrap(True)
        self.detail_content.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setFrameShape(QFrame.NoFrame)
        detail_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        detail_content_container = QWidget()
        detail_content_container.setObjectName("detailContentContainer")
        detail_content_layout = QVBoxLayout(detail_content_container)
        detail_content_layout.setContentsMargins(10, 10, 10, 10)
        detail_content_layout.addWidget(self.detail_content)

        detail_scroll.setWidget(detail_content_container)
        right_layout.addWidget(detail_scroll)

        self.recover_btn = QPushButton("Khôi phục file")
        self.recover_btn.setObjectName("recoverBtn")
        self.recover_btn.setGraphicsEffect(DropShadowEffect(blur_radius=10, y_offset=4)) 

        right_layout.addWidget(self.recover_btn)
    
    def update_details(self, chi_tiet):
        if not chi_tiet:
            self.detail_content.setText("Không có chi tiết.")
            self.recover_btn.setProperty("current_file", None)
            return
            
        text_lines = []
        for key, value in chi_tiet.items():
            field_name = str(key).replace("_", " ").capitalize()
            if isinstance(value, (list, dict)):
                try: 
                    json_str = json.dumps(value, ensure_ascii=False, indent=2)
                    value = f"<pre>{json_str[:500]}...</pre>" 
                except Exception: 
                    value = str(value)
            elif key in ("size"):
                    value = format_size(int(value))
            
            text_lines.append(f"<b>{field_name}:</b> {value}")
            
        self.detail_content.setText("<br>".join(text_lines))
        self.detail_content.setWordWrap(True)
        self.recover_btn.setProperty("current_file", chi_tiet)

    def update_preview(self, chi_tiet, image_path):
        if not chi_tiet:
            self.preview_label.setText("Không có dữ liệu preview")
            return

        file_type = (chi_tiet.get("type") or "").lower()
        file_name = chi_tiet.get("name", "")
        offset = get_best_offset(chi_tiet)
        size = chi_tiet.get("size", 0)
        data = read_file_from_image(image_path, offset, size)


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
class RecoverDeletedApp(QMainWindow):
    home_requested = pyqtSignal()

    def __init__(self, target=None, scan_type="quick", session_file=None):
        super().__init__()
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget) 
        
        self.session_file = session_file
        self.target_info = target
        self.scan_type = scan_type
        self.deleted_files = []
        
        self.setStyleSheet(get_app_stylesheet())
        self.setupUI()

        # --- [ĐÃ XÓA PHẦN DOCK WIDGET Ở ĐÂY CHO GỌN] ---

        if session_file:
            self.load_session(session_file)
        elif self.target_info:
            self.start_scan()
        else:
            self.status_label.setText("Sẵn sàng. (Không có target)")
 
    def setupUI(self):
        """Thiết lập bố cục chuẩn: Sidebar | StackedWidget"""
        # 1. Layout tổng (Ngang)
        main_layout = QHBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 2. Sidebar (Bên trái)
        self.setup_side_bar(main_layout)

        # 3. Stacked Widget (Bên phải - Chứa các trang)
        self.stack = QStackedWidget()

        # --- TRANG 0: FILES VIEW (Bảng + Chi tiết) ---
        self.page_files = QWidget()
        files_layout = QHBoxLayout(self.page_files) # Layout của trang 0
        files_layout.setContentsMargins(0, 0, 0, 0)
        files_layout.setSpacing(0)

        # Setup phần Bảng (Content Frame)
        content_layout = QVBoxLayout()
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(20, 20, 20, 20)
        self.setup_top_bar(content_layout)
        self.setup_table(content_layout)
        
        self.status_label = QLabel("Sẵn sàng.")
        self.status_label.setObjectName("statusLabel")
        content_layout.addWidget(self.status_label)
        
        content_frame = QFrame()
        content_frame.setLayout(content_layout)
        content_frame.setObjectName("mainContentFrame")

        # Setup phần Chi tiết (Detail Panel)
        self.detail_panel = DetailPreviewPanel()

        # ### <--- SỬA Ở ĐÂY: Add vào files_layout (trang con), KHÔNG add vào main_layout
        files_layout.addWidget(content_frame, stretch=3)
        files_layout.addWidget(self.detail_panel, stretch=2)

        # --- TRANG 1: DASHBOARD ---
        self.page_dashboard = QWidget()
        self.dashboard_layout_container = QVBoxLayout(self.page_dashboard)
        self.dashboard_layout_container.setContentsMargins(0, 0, 0, 0)

        # --- Đưa 2 trang vào Stack ---
        self.stack.addWidget(self.page_files)     # Index 0
        self.stack.addWidget(self.page_dashboard) # Index 1

        # ### <--- SỬA Ở ĐÂY: Chỉ add Stack vào layout chính
        main_layout.addWidget(self.stack)

        # Kết nối sự kiện
        self.table.currentCellChanged.connect(self.handle_cell_change)
        self.detail_panel.recover_btn.clicked.connect(self.recover_file)
        
    def setup_side_bar(self, parent_layout):
        """Tạo thanh sidebar bên trái."""
        side_bar = QVBoxLayout()
        side_bar.setSpacing(10)
        side_bar.setAlignment(Qt.AlignTop)
        side_bar.setContentsMargins(15, 20, 15, 20)

        title_label = QLabel("🗂 <b>Forensic Tool</b>", alignment=Qt.AlignCenter)
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        side_bar.addWidget(title_label)
        side_bar.addSpacing(15)

        # --- 1. NÚT HOME (Giữ nguyên: Thoát về giao diện chọn ổ đĩa) ---
        home_btn = QPushButton("🏠 Home")
        home_btn.setObjectName("homeBtn")
        home_btn.setGraphicsEffect(DropShadowEffect(blur_radius=10, y_offset=4, color=QColor(0, 0, 0, 70)))
        home_btn.setFixedHeight(40)
        home_btn.clicked.connect(self.go_home)
        side_bar.addWidget(home_btn)

        # --- Kẻ ngang phân cách ---
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)
        side_bar.addWidget(line1)

        # ============================================================
        # --- (MỚI) NHÓM 2: CHUYỂN ĐỔI GIAO DIỆN (VIEW) ---
        # ============================================================
        lbl_view = QLabel("Chế độ xem:")
        lbl_view.setStyleSheet("color: #888; font-weight: bold; margin-top: 5px; margin-bottom: 5px;")
        side_bar.addWidget(lbl_view)

        # Nút 1: Xem Bảng (Quay về Index 0)
        self.btn_view_list = QPushButton("📄 Danh sách File")
        self.btn_view_list.setGraphicsEffect(DropShadowEffect(blur_radius=10, y_offset=4))
        self.btn_view_list.setFixedHeight(35)
        # Bấm vào thì hiện Stack trang 0
        self.btn_view_list.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        side_bar.addWidget(self.btn_view_list)

        # Nút 2: Xem Dashboard (Sang Index 1)
        self.btn_view_dash = QPushButton("📊 Dashboard")
        self.btn_view_dash.setGraphicsEffect(DropShadowEffect(blur_radius=10, y_offset=4))
        self.btn_view_dash.setFixedHeight(35)
        # Bấm vào thì gọi hàm show_dashboard
        self.btn_view_dash.clicked.connect(self.show_dashboard)
        side_bar.addWidget(self.btn_view_dash)
        
        # --- Kẻ ngang phân cách ---
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        side_bar.addWidget(line2)
        # ============================================================

        # --- 3. CÁC NÚT CHỨC NĂNG (Giữ nguyên) ---
        rescan_btn = QPushButton("🔄 Quét lại")
        rescan_btn.setObjectName("rescanBtn")
        rescan_btn.setGraphicsEffect(DropShadowEffect(blur_radius=10, y_offset=4))
        rescan_btn.setFixedHeight(40)
        rescan_btn.clicked.connect(self.start_scan)
        side_bar.addWidget(rescan_btn)

        save_btn = QPushButton("💾 Lưu phiên")
        save_btn.setObjectName("saveBtn")
        save_btn.setGraphicsEffect(DropShadowEffect(blur_radius=10, y_offset=4))
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self.save_session)
        side_bar.addWidget(save_btn)
        
        recover_all_btn = QPushButton("♻️ Khôi phục tất cả")
        recover_all_btn.setObjectName("recoverAllBtn") 
        recover_all_btn.setGraphicsEffect(DropShadowEffect(blur_radius=10, y_offset=4))
        recover_all_btn.setFixedHeight(40)
        recover_all_btn.clicked.connect(self.recover_all_files)
        side_bar.addWidget(recover_all_btn)

        side_bar.addStretch()

        side_frame = QFrame()
        side_frame.setLayout(side_bar)
        side_frame.setFixedWidth(240)
        side_frame.setObjectName("sidebar")
        
        parent_layout.addWidget(side_frame)
    
    def setup_top_bar(self, parent_layout):
        """Hàm helper để tạo top bar (nút + tìm kiếm)."""
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        
        self.search_box = QLineEdit()
        self.search_box.setObjectName("searchBox")
        self.search_box.setGraphicsEffect(DropShadowEffect(blur_radius=8, y_offset=3, color=QColor(0, 0, 0, 20)))
        
        self.search_box.setPlaceholderText("🔍 Tìm theo tên file...")
        self.search_box.setFixedWidth(300)
        self.search_box.textChanged.connect(self.filter_table)
        top_bar.addWidget(self.search_box)
        
        parent_layout.addLayout(top_bar)

    def setup_table(self, parent_layout):
        """Hàm helper để tạo QTableWidget."""
        table_container = QFrame()
        table_container.setObjectName("tableContainer")
        table_container_layout = QVBoxLayout(table_container)
        table_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget()
        self.table.setObjectName("fileTable") # ID cho QSS
        
        # --- THAY ĐỔI: Tăng lên 6 cột ---
        self.table.setColumnCount(6) 
        self.table.setHorizontalHeaderLabels([
            "Tên", "Loại", "Size", "Ngày tạo", "Độ hoàn thiện", "Tình trạng"
        ])
        # -------------------------------

        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        
        self.table.setSortingEnabled(True)

        table_container_layout.addWidget(self.table)
        
        table_container.setGraphicsEffect(DropShadowEffect(blur_radius=20, y_offset=10, color=QColor(0, 0, 0, 30)))
        
        parent_layout.addWidget(table_container)
    
  # --- [SỬA] THAY THẾ 3 HÀM NÀY ---
    def start_scan(self):
        self.status_label.setText("🔍 Đang khởi tạo quét...")
        self.table.setSortingEnabled(False) 
        
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            
        self.deleted_files = []
        self.table.setRowCount(0)
        
        self.worker = ScanWorker(self.target_info, self.scan_type)
        
        # 1. Tạo và hiện cửa sổ Popup
        self.progress_window = ScanProgressWindow(self)
        self.progress_window.show() 
        
        # 2. Kết nối tín hiệu
        self.progress_window.stop_requested.connect(self.worker.stop)
        self.worker.file_found.connect(self.add_file_to_table)
        self.worker.finished.connect(self.scan_done)
        self.worker.progress.connect(self.update_progress)
        
        self.worker.start()
        print("[INFO] Bắt đầu tiến trình quét mới.")

    def update_progress(self, percent):
        if hasattr(self, "progress_window") and self.progress_window.isVisible():
            self.progress_window.update_progress(percent)

    def scan_done(self):
        # Đóng Popup
        if hasattr(self, "progress_window"):
            self.progress_window.close()
            
        self.table.setSortingEnabled(True)
        self.status_label.setText(f"✅ Hoàn tất - Tổng cộng {len(self.deleted_files)} file bị xóa.")
        QMessageBox.information(self, "Hoàn tất", "Quét file bị xóa hoàn tất!")
   
    def add_file_to_table(self, f):
        orig_index = len(self.deleted_files)
        self.deleted_files.append(f)

        row = self.table.rowCount()
        self.table.insertRow(row)

        # --- Cột 0: Tên file ---
        name_item = QTableWidgetItem(f.get("Tên file", ""))
        name_item.setData(Qt.UserRole, orig_index)
        self.table.setItem(row, 0, name_item)

        # --- Cột 1: Loại ---
        self.table.setItem(row, 1, QTableWidgetItem(f.get("Loại", "")))

        # --- Cột 2: Size ---
        raw_size = 0
        chi_tiet = f.get("Chi tiết", {}) or {}
        try: raw_size = int(chi_tiet.get("size", f.get("Size", 0)) or 0)
        except Exception: raw_size = 0
        size_item = NumericItem(format_size(raw_size))
        size_item.setData(Qt.UserRole, raw_size)
        self.table.setItem(row, 2, size_item)

        # --- Cột 3: Ngày tạo ---
        date_str = f.get("Ngày tạo", "") or ""
        date_item = NumericItem(date_str)
        qdt = QDateTime.fromString(date_str, "dd/MM/yyyy HH:mm:ss")
        timestamp = qdt.toSecsSinceEpoch() if qdt.isValid() else 0
        date_item.setData(Qt.UserRole, int(timestamp))
        self.table.setItem(row, 3, date_item)

        # ==========================================================
        # --- Cột 4: Độ hoàn thiện (SỬA CHỮA MẠNH MẼ) ---
        # ==========================================================
        status_str = str(f.get("Tình trạng", "") or "")
        raw_val = None

        # 1. Tìm trong các key phổ biến ở cả 'f' và 'chi_tiet'
        # Các từ khóa có thể: integrity, completeness, percent, rate
        keys_to_check = ["integrity", "completeness", "percent", "recovery_rate"]
        for k in keys_to_check:
            val = f.get(k) or chi_tiet.get(k)
            if val is not None:
                raw_val = val
                break
        
        # 2. Nếu không tìm thấy key, dùng Regex tìm số % trong chuỗi Tình trạng
        # Ví dụ: "100%", "Good (90%)"
        if raw_val is None:
            match = re.search(r"(\d+)\s*%", status_str)
            if match:
                raw_val = match.group(1)
            elif status_str.replace(".", "", 1).isdigit(): # Nếu status chỉ là số
                 raw_val = status_str

        # 3. Chuyển đổi sang số nguyên (int)
        final_score = 0
        try:
            if raw_val is not None:
                # Xóa ký tự % và khoảng trắng, ép kiểu float rồi int
                clean_str = str(raw_val).replace("%", "").strip()
                final_score = int(float(clean_str))
            else:
                # 4. Fallback: Nếu không có số, đoán theo từ khóa
                s_lower = status_str.lower()
                if "excellent" in s_lower or "tốt" in s_lower: final_score = 100
                elif "good" in s_lower or "khá" in s_lower: final_score = 85
                elif "average" in s_lower or "trung bình" in s_lower: final_score = 50
                elif "poor" in s_lower or "kém" in s_lower: final_score = 25
                elif "lost" in s_lower or "đè" in s_lower: final_score = 0
        except Exception:
            final_score = 0

        # Giới hạn 0-100
        final_score = max(0, min(100, final_score))

        # Hiển thị
        comp_item = NumericItem(f"{final_score}%")
        comp_item.setData(Qt.UserRole, final_score)
        
        # Tô màu
        if final_score >= 90:
            comp_item.setForeground(QColor("#2e7d32")) # Xanh đậm
            comp_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
        elif final_score >= 50:
            comp_item.setForeground(QColor("#ef6c00")) # Cam
        else:
            comp_item.setForeground(QColor("#c62828")) # Đỏ

        self.table.setItem(row, 4, comp_item)
        # ==========================================================

        # --- Cột 5: Tình trạng ---
        self.table.setItem(row, 5, QTableWidgetItem(status_str))

        if row % 100 == 0:
            self.status_label.setText(f"Tìm thấy {len(self.deleted_files)} file bị xóa...")      

    def handle_cell_change(self, current_row, current_col, prev_row, prev_col):
        if current_row < 0: return
        
        name_item = self.table.item(current_row, 0)
        if not name_item: return
        
        orig_index = name_item.data(Qt.UserRole)
        if orig_index is None or orig_index >= len(self.deleted_files): return
            
        chi_tiet = self.deleted_files[orig_index].get("Chi tiết", {})
        image_path = self.target_info.get("path") if self.target_info else None

        self.detail_panel.update_details(chi_tiet)
        self.detail_panel.update_preview(chi_tiet, image_path)
        
    def recover_file(self):
        chi_tiet = self.detail_panel.recover_btn.property("current_file")
        if not chi_tiet:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một file để khôi phục.")
            return

        file_name = chi_tiet.get("name", "recovered_file")
        temp_path = chi_tiet.get("temp_path") or os.path.join("recovered_files", file_name)

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Chọn nơi lưu file khôi phục", file_name
        )
        if not save_path:
            return

        try:
            log_action(f"Đang khôi phục file: {file_name} -> {save_path}") # <--- Thêm dòng này
            if os.path.exists(temp_path):
                with open(temp_path, "rb") as src, open(save_path, "wb") as dst:
                    dst.write(src.read())
                QMessageBox.information(
                    self, "Hoàn tất",
                    f"File đã được khôi phục (copy từ file tạm):\n{save_path}"
                )
                log_action(f"Thành công: Copy từ file tạm ({file_name})") # <--- Thêm dòng này
                return

            image_path = self.target_info.get("path")
            offset = get_best_offset(chi_tiet)
            size = chi_tiet.get("size", 0)
            data = read_file_from_image(image_path, offset, size)

            with open(save_path, "wb") as f:
                f.write(data)
            QMessageBox.information(
                self, "Hoàn tất",
                f"File đã được khôi phục (đọc từ image):\n{save_path}"
            )
            log_action(f"Thành công: Đọc trực tiếp từ ổ đĩa ({file_name})") # <--- Thêm dòng này
        except Exception as e:
            log_action(f"Thất bại khi khôi phục {file_name}: {e}", "error") # <--- Thêm dòng này
            QMessageBox.warning(self, "Lỗi", f"Không thể khôi phục file:\n{e}")

    def recover_all_files(self):
        """Khôi phục tất cả các file trong danh sách `self.deleted_files` vào một thư mục."""
        if not self.deleted_files:
            QMessageBox.warning(self, "Lỗi", "Không có file nào để khôi phục.")
            return

        save_dir = QFileDialog.getExistingDirectory(
            self, 
            "Chọn thư mục để lưu tất cả file khôi phục",
            os.path.expanduser("~") # Bắt đầu ở thư mục home
        )
        if not save_dir:
            return

        # Kiểm tra xem có cần image_path không và có image_path không
        image_path = self.target_info.get("path") if self.target_info else None
        needs_image_path = False
        if not image_path:
            for file_info in self.deleted_files:
                chi_tiet = file_info.get("Chi tiết", {})
                file_name = chi_tiet.get("name", "temp")
                temp_path = chi_tiet.get("temp_path") or os.path.join("recovered_files", file_name)
                if not os.path.exists(temp_path):
                    needs_image_path = True
                    break
        
        if needs_image_path and not image_path:
            QMessageBox.critical(self, "Lỗi nghiêm trọng", 
                               "Không có đường dẫn đến file image (target) và "
                               "một số file không có file tạm. Không thể tiếp tục khôi phục tất cả.")
            return
        
        total_files = len(self.deleted_files)
        success_count = 0
        fail_count = 0

        self.status_label.setText(f"Đang chuẩn bị khôi phục {total_files} file...")
        QApplication.processEvents()
        log_action(f"Bắt đầu khôi phục tất cả ({len(self.deleted_files)} files) vào: {save_dir}") # <--- Thêm dòng này
        for i, file_info in enumerate(self.deleted_files):
            self.status_label.setText(f"Đang khôi phục {i+1}/{total_files}...")
            QApplication.processEvents() # Cho phép UI cập nhật

            try:
                chi_tiet = file_info.get("Chi tiết", {})
                if not chi_tiet:
                    fail_count += 1
                    continue

                file_name = chi_tiet.get("name", f"recovered_file_{i}")
                # Đảm bảo tên file hợp lệ (loại bỏ ký tự không mong muốn)
                file_name = re.sub(r'[\\/:*?"<>|]', '_', file_name)
                if not file_name: file_name = f"recovered_file_{i}"

                temp_path = chi_tiet.get("temp_path") or os.path.join("recovered_files", file_name)
                
                # Xử lý trùng tên
                base, ext = os.path.splitext(file_name)
                count = 1
                output_path = os.path.join(save_dir, file_name)
                while os.path.exists(output_path):
                    output_path = os.path.join(save_dir, f"{base} ({count}){ext}")
                    count += 1

                # Thực hiện khôi phục (copy từ `recover_file`)
                if os.path.exists(temp_path):
                    with open(temp_path, "rb") as src, open(output_path, "wb") as dst:
                        dst.write(src.read())
                else:
                    # Chúng ta đã check image_path ở trên
                    offset = get_best_offset(chi_tiet)
                    size = chi_tiet.get("size", 0)
                    data = read_file_from_image(image_path, offset, size)
                    with open(output_path, "wb") as f:
                        f.write(data)
                log_action(f"[Thành công] Khôi phục file {file_name} -> {output_path}") # <--- Thêm dòng này
                success_count += 1
            
            except Exception as e:
                print(f"[Lỗi] Khôi phục file {file_name} thất bại: {e}")
                log_action(f"Lỗi khôi phục file {file_name}: {e}", "error") # <--- Thêm dòng này
                fail_count += 1
        
        self.status_label.setText(f"Hoàn tất! Khôi phục thành công {success_count}/{total_files} file.")
        QMessageBox.information(self, "Hoàn tất", 
                              f"Quá trình khôi phục tất cả đã hoàn tất.\n"
                              f"Thành công: {success_count}\n"
                              f"Thất bại: {fail_count}\n\n"
                              f"File được lưu tại: {save_dir}")
        log_action(f"Kết thúc khôi phục hàng loạt. Thành công: {success_count}, Lỗi: {fail_count}") # <--- Thêm dòng này
    def filter_table(self, text):
        text = text.strip().lower()
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)

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

            files_to_load = []
            if isinstance(session_data, dict) and "deleted_files_formatted" in session_data:
                files_to_load = session_data.get("deleted_files_formatted", [])
                loaded_target = session_data.get("target_info")
                if loaded_target: self.target_info = loaded_target 
                self.scan_type = session_data.get("scan_type", "quick")
            elif isinstance(session_data, list):
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

            self.deleted_files = [] 
            self.table.setSortingEnabled(False)
            self.table.setRowCount(0)
            
            for file_info in files_to_load:
                self.add_file_to_table(file_info)

            # Kích hoạt lại sắp xếp sau khi chèn dữ liệu.
            self.table.setSortingEnabled(True)

            status_text = f"📂 Đã tải phiên: {os.path.basename(file_path)} ({len(self.deleted_files)} file)"
            if self.target_info:
                status_text += f" | Target: {self.target_info.get('path', 'N/A')}"
            else:
                status_text += " | (Không rõ target - Chế độ chỉ xem)"
            self.status_label.setText(status_text)
            
            self.current_session_file = file_path
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải phiên:\n{e}")

    def go_home(self):
        # Nếu đang quét thì hỏi
        if hasattr(self, 'worker') and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Dừng quét?",
                "Quá trình quét đang chạy. Bạn có chắc muốn quay về Home?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

            self.worker.stop()
            self.worker.wait()

        # ✅ CHỈ XÓA FILE TẠM
        self.cleanup_recovered_files()

        # ❌ KHÔNG đụng deleted_files
        # ❌ KHÔNG reset table

        self.home_requested.emit()
    
   # ... (Trong class RecoverDeletedApp) ...
    def cleanup_recovered_files(self):
        temp_dir = "recovered_files"
        if not os.path.exists(temp_dir):
            return

        try:
            for fname in os.listdir(temp_dir):
                fpath = os.path.join(temp_dir, fname)
                if os.path.isfile(fpath):
                    os.remove(fpath)
            log_action("Đã dọn dẹp thư mục recovered_files/ (Xóa file tạm)") # <--- Thay print bằng log_action
        except Exception as e:
            log_action(f"Lỗi dọn dẹp file tạm: {e}", "error") #
    def show_dashboard(self):
        """Hiển thị Dashboard và kết nối sự kiện click"""
        self.stack.setCurrentIndex(1)
        
        # Xóa cũ
        while self.dashboard_layout_container.count():
            child = self.dashboard_layout_container.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        
        try:
            dashboard = DashboardWidget() 
            # [QUAN TRỌNG] Kết nối tín hiệu từ Dashboard
            dashboard.filter_requested.connect(self.handle_dashboard_filter)
            
            self.dashboard_layout_container.addWidget(dashboard, 1) 
        except Exception as e:
            self.dashboard_layout_container.addWidget(QLabel(f"Lỗi: {e}"))


    def handle_dashboard_filter(self, category):
     
        print(f"User selected category: {category}") # Debug
        
        # 1. Chuyển về trang danh sách file (Index 0)
        self.stack.setCurrentIndex(0)
        
        # 2. Reset ô tìm kiếm
        self.search_box.clear()
        self.search_box.setText(category) 
        
        # Nếu bạn muốn filter CHÍNH XÁC theo cột Loại (Cột 1), hãy sửa hàm filter_table:
        self.filter_table_by_type(category)

    def filter_table_by_type(self, category):
        """Hàm lọc nâng cao chỉ dựa trên cột Loại (Cột 1)"""
        # Định nghĩa các đuôi file cho từng nhóm
        extensions = {
            "Image": ['jpg','jpeg','png','bmp','gif','webp','svg','tiff'],
            "Document": ['doc','docx','pdf','txt','xls','xlsx','ppt','pptx'],
            "Music": ['mp3','wav','flac','aac','ogg'],
            "Archive": ['zip','rar','7z','tar','gz','iso'],
            "Other": [] # Other là cái còn lại
        }
        
        target_exts = extensions.get(category, [])
        
        for row in range(self.table.rowCount()):
            # Lấy item cột Loại (Cột 1)
            type_item = self.table.item(row, 1) 
            if not type_item: continue
            
            file_type = type_item.text().lower()
            
            should_show = False
            if category == "Other":
                # Nếu là Other, hiện những cái KHÔNG nằm trong các nhóm trên
                all_known = [e for sublist in extensions.values() for e in sublist]
                if file_type not in all_known: should_show = True
            else:
                # Nếu thuộc danh sách đuôi file của nhóm đó
                if file_type in target_exts: should_show = True
            
            self.table.setRowHidden(row, not should_show)
               
    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Thoát ứng dụng?",
                "Quá trình quét đang chạy. Bạn có chắc muốn thoát?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return

            self.worker.stop()
            self.worker.wait()

        # ✅ THOÁT LÀ XÓA FILE TẠM
        self.cleanup_recovered_files()

        event.accept()
