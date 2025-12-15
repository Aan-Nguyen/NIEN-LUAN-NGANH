from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QFrame, QTreeWidget, QHeaderView, QMessageBox,
    QGraphicsDropShadowEffect, QTreeWidgetItem, QSizePolicy, QToolButton 
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize # Thêm QSize
from PyQt5.QtGui import QFont, QPixmap, QColor, QIcon 
import sys, json, os, subprocess
from styles import get_app_stylesheet
# Giữ nguyên import config
from config import JSON_PATH, TREE_HEADERS, IMAGE_PATH_INTERNAL, IMAGE_PATH_USB, IMAGE_PATH_PARTITION 

sys.stdout.reconfigure(encoding='utf-8')

# =========================== Hiệu ứng đổ bóng ===========================
class DropShadowEffect(QGraphicsDropShadowEffect):
    def __init__(self, color=QColor(0, 0, 0, 80), blur_radius=18, x_offset=0, y_offset=6):
        super().__init__()
        self.setBlurRadius(blur_radius)
        self.setColor(color)
        self.setOffset(x_offset, y_offset)

# =========================== Giao diện chính ===========================
class RecoverApp(QWidget):
    scan_requested = pyqtSignal(dict, str)
    sessions_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.disk_data = {}
        # sidebar visible flag (not strictly needed, but handy)
        self.sidebar_visible = True

        # Theme
        self.setStyleSheet(get_app_stylesheet())

        # Setup UI + load data
        self.setupUI()
        self.load_data()

        # connect tree click
        self.tree.itemClicked.connect(self.show_detail)

    def setupUI(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ---------------------- SIDEBAR ----------------------
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar_expanded_width = 240
        self.sidebar_collapsed_width = 60
        # start expanded
        self.sidebar.setFixedWidth(self.sidebar_expanded_width)
        # ensure it never collapses to 0 (so hamburger always visible)
        self.sidebar.setMinimumWidth(self.sidebar_collapsed_width)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(12)

        # ------- Header Sidebar (Hamburger + Title) -------
        header_row = QHBoxLayout()

        # Hamburger / Menu button (always visible)
        self.menu_btn = QToolButton()
        self.menu_btn.setObjectName("hamburgerBtn")
        # try to load icon, else fallback to text
        icon_path = os.path.join("icons", "menu.png")
        if os.path.exists(icon_path):
            self.menu_btn.setIcon(QIcon(icon_path))
        else:
            self.menu_btn.setText("☰")
            # slightly larger when text
        self.menu_btn.setIconSize(QSize(22, 22))
        self.menu_btn.setCursor(Qt.PointingHandCursor)
        self.menu_btn.setToolTip("Ẩn/Hiện menu")
        self.menu_btn.clicked.connect(self.toggle_left_panel)

        self.sidebar_title = QLabel("Recover File")
        self.sidebar_title.setFont(QFont("Segoe UI Semibold", 15))

        header_row.addWidget(self.menu_btn, 0, Qt.AlignLeft)
        header_row.addSpacing(8)
        header_row.addWidget(self.sidebar_title)
        header_row.addStretch()

        sidebar_layout.addLayout(header_row)
        sidebar_layout.addSpacing(15)

        # -------- Buttons (kept in a list for hide/show) --------
        def make_button(text, object_name):
            btn = QPushButton(text)
            btn.setObjectName(object_name)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(42)
            btn.setGraphicsEffect(DropShadowEffect(blur_radius=10, y_offset=4))
            return btn

        self.reset_btn = make_button("🔄 Làm mới", "resetBtn")
        self.scan_btn = make_button("🧭 Quét ngay", "scanBtn")
        self.work_btn = make_button("📁 Phiên làm việc", "workBtn")

        # connect signals to functions (keeps behavior)
        self.reset_btn.clicked.connect(self.scan_disks_from_script)
        self.scan_btn.clicked.connect(self.scan_model)
        self.work_btn.clicked.connect(self.open_session_file)

        # list for hide/show when collapsed
        self.sidebar_buttons = [self.reset_btn, self.scan_btn, self.work_btn]

        sidebar_layout.addWidget(self.reset_btn)
        sidebar_layout.addWidget(self.scan_btn)
        sidebar_layout.addWidget(self.work_btn)
        sidebar_layout.addStretch()

        main_layout.addWidget(self.sidebar)

        # ---------------------- CONTENT ----------------------
        content = QFrame()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header_h_layout = QHBoxLayout()
        title_label = QLabel("💾 Thiết bị / Ổ đĩa khả dụng")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header_h_layout.addWidget(title_label)
        header_h_layout.addStretch()
        content_layout.addLayout(header_h_layout)

        # Tree container
        tree_container = QFrame()
        tree_container.setObjectName("diskTreeContainer")
        tree_container_layout = QVBoxLayout(tree_container)
        tree_container_layout.setContentsMargins(5, 5, 5, 5)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(TREE_HEADERS)
        self.tree.header().setSectionResizeMode(QHeaderView.Stretch)
        tree_container_layout.addWidget(self.tree)

        content_layout.addWidget(tree_container)
        main_layout.addWidget(content)

        # ---------------------- RIGHT PANEL ----------------------
        self.right_panel = QFrame()
        self.right_panel.setObjectName("rightPanel")
        self.right_panel.setFixedWidth(280)
        right_layout = QVBoxLayout(self.right_panel)

        right_layout.addWidget(QLabel("<b>THÔNG TIN CHI TIẾT</b>"))
        right_layout.addSpacing(10)

        self.detail_image = QLabel(alignment=Qt.AlignCenter)
        self.detail_image.setFixedSize(240, 130)

        self.detail_info = QLabel("Chọn thiết bị hoặc phân vùng để xem chi tiết.")
        self.detail_info.setWordWrap(True)

        right_layout.addWidget(self.detail_image)
        right_layout.addWidget(self.detail_info)
        right_layout.addStretch()

        main_layout.addWidget(self.right_panel)

    def toggle_left_panel(self):
        """
        Khi thu gọn: giảm width về collapsed_width, ẩn title + các nút (nhưng KHÔNG ẩn menu_btn).
        Khi mở: phục hồi width, hiện title + nút.
        """
        current_width = self.sidebar.width()
        # Use a threshold (100) to decide state (robust vs tiny widths)
        if current_width > 100:
            # THU GỌN: giữ hamburger visible, ẩn title + buttons
            self.sidebar.setFixedWidth(self.sidebar_collapsed_width)
            self.sidebar_title.hide()
            for btn in self.sidebar_buttons:
                btn.hide()
            # ensure menu button still clickable / visible
            self.menu_btn.show()
        else:
            # MỞ RỘNG
            self.sidebar.setFixedWidth(self.sidebar_expanded_width)
            self.sidebar_title.show()
            for btn in self.sidebar_buttons:
                btn.show()

    # ==================== Logic gốc giữ nguyên ====================
    def go_home(self): 
        self.scan_requested.emit({}, "")

    def open_session_file(self):
        self.sessions_requested.emit()

    def get_selected_disk_info(self):
        item = self.tree.currentItem()
        if not item:
            return None
        data = item.data(0, Qt.UserRole)
        if not data:
            return None
        if data["type"] == "disk":
            return self.disk_data["disks"][data["index"]]
        elif data["type"] == "volume":
            disk = self.disk_data["disks"][data["disk_index"]]
            return disk["volumes"][data["vol_index"]]
        return None

    def scan_model(self):
        selected = self.get_selected_disk_info()
        if not selected:
            QMessageBox.warning(self, "Chưa chọn phân vùng", "Vui lòng chọn ổ đĩa hoặc phân vùng để quét.")
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Chọn chế độ quét")
        msg.setText("Chọn kiểu quét:")

        quick_btn = msg.addButton("Quét nhanh", QMessageBox.AcceptRole)
        deep_btn = msg.addButton("Quét sâu", QMessageBox.DestructiveRole)
        cancel_btn = msg.addButton("Huỷ", QMessageBox.RejectRole)  # nút giúp X hoạt động

        msg.exec_()

        if msg.clickedButton() == cancel_btn:
            return  # Người dùng bấm X hoặc Huỷ

        scan_type = "quick" if msg.clickedButton() == quick_btn else "deep"
        self.scan_requested.emit(selected, scan_type)


    def scan_disks_from_script(self):
        # không raise exception khi script lỗi
        subprocess.run([sys.executable, "disk_info.py"], check=False)
        self.load_data()

    def load_data(self):
        self.tree.clear()
        self.disk_data = {}
        if not os.path.exists(JSON_PATH):
            QMessageBox.warning(self, "Lỗi", f"Không tìm thấy file JSON:\n{JSON_PATH}")
            return
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                self.disk_data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi đọc file", str(e))
            return
        self.populate_tree()
        self.show_default_detail()

    def populate_tree(self):
        self.tree.clear()
        for i, disk in enumerate(self.disk_data.get("disks", [])):
            disk_item = QTreeWidgetItem([
                f"🖴 {disk.get('model', 'Unknown')}",
                "Hardware Disk",
                disk.get("protocol", "N/A"),
                f"{disk.get('size_str', disk.get('size', 0))}"
            ])
            disk_item.setData(0, Qt.UserRole, {"type": "disk", "index": i})
            self.tree.addTopLevelItem(disk_item)
            for j, vol in enumerate(disk.get("volumes", [])):
                display_name = f"{vol.get('label', 'No name')} ({vol.get('letter', '')})"
                vol_item = QTreeWidgetItem([
                    f"📂 {display_name}",
                    "Logical Volume",
                    vol.get("filesystem", "N/A"),
                    f"{vol.get('size_str', vol.get('size', 0))}"
                ])
                vol_item.setData(0, Qt.UserRole, {"type": "volume", "disk_index": i, "vol_index": j})
                disk_item.addChild(vol_item)
        self.tree.expandAll()

    def show_default_detail(self):
        self.detail_image.setText("NO IMAGE")
        self.detail_image.setPixmap(QPixmap())
        self.detail_info.setText("Chọn thiết bị hoặc phân vùng bên trái để xem thông tin chi tiết.")

    def show_detail(self, item, column):
        data = item.data(0, Qt.UserRole)
        if not data:
            return self.show_default_detail()
        if data["type"] == "disk":
            target = self.disk_data["disks"][data["index"]]
            self.update_detail_panel(target, "disk", "USB" in target.get("protocol", "").upper())
        else:
            disk = self.disk_data["disks"][data["disk_index"]]
            target = disk["volumes"][data["vol_index"]]
            self.update_detail_panel(target, "volume")

    def update_detail_panel(self, target, type_, is_usb=False):
        title = "🔌 Thiết bị USB ngoài" if (type_ == "disk" and is_usb) else (
            "🖴 Thiết bị vật lý" if type_ == "disk" else "📂 Phân vùng logic")
        img_path = IMAGE_PATH_USB if (type_ == "disk" and is_usb) else (
            IMAGE_PATH_INTERNAL if type_ == "disk" else IMAGE_PATH_PARTITION)
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            self.detail_image.setPixmap(pixmap.scaled(
                self.detail_image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.detail_image.setText("")
        else:
            self.detail_image.setText("IMAGE NOT FOUND")

        html = f"<h3>{title}</h3><hr style='border: none; border-top: 1px solid #dcdfe3; margin: 5px 0;'>"
        html += "<div style='line-height: 1.4;'>"
        for k, v in target.items():
            if k in ("volumes", "name", "size"):
                continue
            if k in ("size_gb", "free_gb") and isinstance(v, (int, float)):
                v = f"{v:.2f} GB"
            html += f"<p style='margin: 0; padding: 2px 0;'><b>{k.replace('_', ' ').capitalize()}:</b> {v}</p>"
        html += "</div>"

        self.detail_info.setText(html)
