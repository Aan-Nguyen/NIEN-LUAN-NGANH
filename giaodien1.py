# main.py
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QTreeWidget, QTreeWidgetItem, QListWidget,
    QListWidgetItem, QFrame, QHeaderView, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
import sys, json, os

from styles import get_app_stylesheet
from config import (
    JSON_PATH, TREE_HEADERS, MENU_ITEMS,
    IMAGE_PATH_INTERNAL, IMAGE_PATH_USB, IMAGE_PATH_PARTITION
)

sys.stdout.reconfigure(encoding='utf-8')


class RecoverApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Recover File App")
        self.resize(1100, 650)
        self.disk_data = {}

        self.setStyleSheet(get_app_stylesheet())
        self.setupUI()
        self.load_data()

        self.tree.itemClicked.connect(self.show_detail)

    # ===================== GIAO DIỆN =====================
    def setupUI(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- Sidebar ---
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(20)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        title = QLabel("🧭 <b>Recover File</b>")
        title.setFont(QFont("Segoe UI", 14))
        title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title)

        menu = QListWidget()
        menu.setFixedWidth(200)
        for name in MENU_ITEMS:
            item = QListWidgetItem(name)
            item.setTextAlignment(Qt.AlignLeft)
            menu.addItem(item)
        sidebar_layout.addWidget(menu)

        sidebar = QFrame()
        sidebar.setLayout(sidebar_layout)
        sidebar.setFixedWidth(220)
        sidebar.setObjectName("sidebar")

        # --- Tree + Buttons ---
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("Thiết bị / Ổ đĩa có sẵn")
        title_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        content_layout.addWidget(title_label)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(TREE_HEADERS)
        self.tree.header().setSectionResizeMode(QHeaderView.Stretch)
        content_layout.addWidget(self.tree)

        btn_layout = QHBoxLayout()
        self.reset_btn = QPushButton("🔄 Reset")
        self.reset_btn.clicked.connect(self.load_data)
        self.scan_btn = QPushButton("▶ Quét ngay")
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.scan_btn)
        content_layout.addLayout(btn_layout)

        # --- Right Info Panel ---
        right_panel = QFrame()
        right_panel.setFixedWidth(260)
        right_panel.setObjectName("rightPanel")

        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 15, 15, 15)

        right_layout.addWidget(QLabel("<b>THÔNG TIN CHI TIẾT</b>"))

        self.detail_image = QLabel("NO IMAGE", alignment=Qt.AlignCenter)
        self.detail_image.setFixedSize(220, 100)
        self.detail_image.setStyleSheet(
            "border:1px solid #ccc; background-color:#eef1f5; border-radius:5px;"
        )
        right_layout.addWidget(self.detail_image)

        self.detail_info = QLabel("Chọn thiết bị/phân vùng để xem chi tiết.")
        self.detail_info.setWordWrap(True)
        right_layout.addWidget(self.detail_info)
        right_layout.addStretch()

        # --- Tổng hợp ---
        main_layout.addWidget(sidebar)
        main_layout.addLayout(content_layout)
        main_layout.addWidget(right_panel)

    # ===================== XỬ LÝ DỮ LIỆU =====================
    def load_data(self):
        """Đọc dữ liệu JSON và hiển thị lên TreeWidget."""
        self.tree.clear()
        self.disk_data = {"disks": []}

        if not os.path.exists(JSON_PATH):
            QMessageBox.warning(self, "Lỗi", f"Không tìm thấy file JSON:\n{JSON_PATH}")
            return

        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                self.disk_data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi đọc file", str(e))
            return

        for i, disk in enumerate(self.disk_data.get("disks", [])):
            disk_item = QTreeWidgetItem([
                f"🖴 {disk.get('model', 'Unknown Disk')}",
                "Hardware Disk",
                disk.get("protocol", "N/A"),
                f"{disk.get('size_gb', 0.0):.2f} GB"
            ])
            disk_item.setData(0, Qt.UserRole, {"type": "disk", "index": i})
            self.tree.addTopLevelItem(disk_item)

            for j, vol in enumerate(disk.get("volumes", [])):
                name = vol.get("label", "Không có tên")
                letter = vol.get("letter", "")
                display_name = f"{name} ({letter})" if letter else name
                vol_item = QTreeWidgetItem([
                    f"   📂 {display_name}",
                    "Logical Volume",
                    vol.get("filesystem", "N/A"),
                    f"{vol.get('size_gb', 0.0):.2f} GB"
                ])
                vol_item.setData(0, Qt.UserRole, {"type": "volume", "disk_index": i, "vol_index": j})
                disk_item.addChild(vol_item)

        self.tree.expandAll()
        self.show_default_detail()
        print(f"✅ Đã nạp {len(self.disk_data['disks'])} ổ đĩa thành công.")

    def show_default_detail(self):
        self.detail_image.setText("NO IMAGE")
        self.detail_image.setPixmap(QPixmap())
        self.detail_info.setText(
            "Chọn thiết bị hoặc phân vùng bên trái để xem thông tin chi tiết."
        )

    # ===================== HIỂN THỊ CHI TIẾT =====================
    def show_detail(self, item, column):
        data = item.data(0, Qt.UserRole)
        if not data:
            self.show_default_detail()
            return

        # Xác định loại thiết bị và dữ liệu nguồn
        if data["type"] == "disk":
            target = self.disk_data["disks"][data["index"]]
            is_usb = "USB" in target.get("protocol", "").upper()
            img_path = IMAGE_PATH_USB if is_usb else IMAGE_PATH_INTERNAL
            title = "🔌 THIẾT BỊ USB NGOÀI" if is_usb else "🖴 THIẾT BỊ VẬT LÝ"
        else:
            disk = self.disk_data["disks"][data["disk_index"]]
            target = disk["volumes"][data["vol_index"]]
            img_path = IMAGE_PATH_PARTITION
            title = "📂 PHÂN VÙNG LOGIC"

        # Tạo HTML hiển thị
        html = [f"<h3>{title}</h3><div style='background:#fff;padding:10px;border:1px solid #ddd;border-radius:5px;'>"]
        for key, val in target.items():
            if key in ("volumes", "name"): 
                continue
            label = key.replace("_", " ").capitalize()
            value = val

            if key in ("size_gb", "free_gb"):
                value = f"{val:.2f} GB"
            elif key == "label" and data["type"] == "volume":
                letter = target.get("letter", "")
                value = f"<b>{val} ({letter})</b>"

            html.append(f"<b>{label}:</b> {value}<br>")
        html.append("</div>")

        # Cập nhật ảnh
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            self.detail_image.setPixmap(pixmap.scaled(
                self.detail_image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
            self.detail_image.setText("")
        else:
            self.detail_image.setText("IMAGE NOT FOUND")

        self.detail_info.setText("".join(html))




