# giaodien1.py
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
import sys, json, os, subprocess
from styles import get_app_stylesheet
from config import JSON_PATH, TREE_HEADERS, MENU_ITEMS, IMAGE_PATH_INTERNAL, IMAGE_PATH_USB, IMAGE_PATH_PARTITION

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

    def setupUI(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)

        # Sidebar
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(20)
        sidebar_layout.setContentsMargins(10,20,10,20)
        sidebar_layout.addWidget(QLabel("🧭 <b>Recover File</b>", alignment=Qt.AlignCenter, font=QFont("Segoe UI",14)))

        menu = QListWidget()
        menu.setFixedWidth(200)
        for name in MENU_ITEMS: menu.addItem(QListWidgetItem(name))
        sidebar_layout.addWidget(menu)
         # Home button
        home_btn = QPushButton("🏠 Home")
        home_btn.clicked.connect(self.go_home)
        sidebar_layout.addWidget(home_btn)
        
    
        sidebar = QFrame()
        sidebar.setLayout(sidebar_layout)
        sidebar.setFixedWidth(220)
        sidebar.setObjectName("sidebar")

        # Content
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20,20,20,20)
        content_layout.addWidget(QLabel("Thiết bị / Ổ đĩa có sẵn", font=QFont("Segoe UI",13,QFont.Bold)))

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(TREE_HEADERS)
        self.tree.header().setSectionResizeMode(QHeaderView.Stretch)
        content_layout.addWidget(self.tree)

        btn_layout = QHBoxLayout()
        for text, func in [("🔄 Reset", self.scan_disks_from_script), ("▶ Quét ngay", self.scan_model)]:
            btn = QPushButton(text)
            btn.clicked.connect(func)
            btn_layout.addWidget(btn)
        content_layout.addLayout(btn_layout)

        # Right panel
        right_panel = QFrame()
        right_panel.setFixedWidth(260)
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15,15,15,15)
        right_layout.addWidget(QLabel("<b>THÔNG TIN CHI TIẾT</b>"))

        self.detail_image = QLabel("NO IMAGE", alignment=Qt.AlignCenter)
        self.detail_image.setFixedSize(220,100)
        self.detail_image.setStyleSheet("border:1px solid #ccc; background:#eef1f5; border-radius:5px;")
        right_layout.addWidget(self.detail_image)

        self.detail_info = QLabel("Chọn thiết bị/phân vùng để xem chi tiết.")
        self.detail_info.setWordWrap(True)
        right_layout.addWidget(self.detail_info)
        right_layout.addStretch()

        main_layout.addWidget(sidebar)
        main_layout.addLayout(content_layout)
        main_layout.addWidget(right_panel)

# ===================== Chuyển về Home =====================
    def go_home(self):
        self.show()  # Hiển thị lại Home
        if hasattr(self, "next_window") and self.next_window.isVisible():
            self.next_window.close()  # Đóng giao diện quét nếu đang mở
    # ===================== Lấy phân vùng/ổ đang chọn =====================
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
        else:
            return None

    # ===================== Quét ngay =====================
    def scan_model(self):
        selected_info = self.get_selected_disk_info()
        if not selected_info:
            QMessageBox.warning(self, "Chưa chọn phân vùng", "Vui lòng chọn ổ đĩa hoặc phân vùng để quét.")
            return

        # Hộp thoại chọn kiểu quét
        msg = QMessageBox(self)
        msg.setWindowTitle("Chọn chế độ quét")
        msg.setText("Chọn kiểu quét mà bạn muốn thực hiện:")
        quick_btn = msg.addButton("⚡ Quét nhanh", QMessageBox.AcceptRole)
        deep_btn = msg.addButton("🔍 Quét sâu", QMessageBox.DestructiveRole)
        msg.exec_()

        clicked = msg.clickedButton()
        scan_type = "quick" if clicked == quick_btn else "deep"

        from giaodien2 import RecoverDeletedApp
        self.next_window = RecoverDeletedApp(target=selected_info, scan_type=scan_type)
        self.next_window.show()
        self.close()

    # ===================== Chạy script reset quét ổ =====================
    def scan_disks_from_script(self):
        subprocess.run([sys.executable, "disk_info.py"], check=True)
        self.load_data()

    # ===================== Load dữ liệu từ JSON =====================
    def load_data(self):
        self.tree.clear()
        self.disk_data = {"disks":[]}
        if not os.path.exists(JSON_PATH):
            QMessageBox.warning(self,"Lỗi",f"Không tìm thấy file JSON:\n{JSON_PATH}")
            return
        try:
            with open(JSON_PATH,"r",encoding="utf-8") as f:
                self.disk_data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self,"Lỗi đọc file",str(e))
            return
        self.populate_tree()
        self.show_default_detail()

    def populate_tree(self):
        for i,disk in enumerate(self.disk_data.get("disks",[])):
            disk_item = QTreeWidgetItem([f"🖴 {disk.get('model','Unknown')}", "Hardware Disk",
                                         disk.get("protocol","N/A"), f"{disk.get('size_str', disk.get('size',0))}"])
            disk_item.setData(0,Qt.UserRole,{"type":"disk","index":i})
            self.tree.addTopLevelItem(disk_item)
            for j,vol in enumerate(disk.get("volumes",[])):
                name,letter = vol.get("label","Không có tên"), vol.get("letter","")
                display_name = f"{name} ({letter})" if letter else name
                vol_item = QTreeWidgetItem([f"   📂 {display_name}","Logical Volume",
                                            vol.get("filesystem","N/A"),f"{vol.get('size_str', vol.get('size',0))}"])
                vol_item.setData(0,Qt.UserRole,{"type":"volume","disk_index":i,"vol_index":j})
                disk_item.addChild(vol_item)
        self.tree.expandAll()

    # ===================== Hiển thị chi tiết =====================
    def show_default_detail(self):
        self.detail_image.setText("NO IMAGE")
        self.detail_image.setPixmap(QPixmap())
        self.detail_info.setText("Chọn thiết bị hoặc phân vùng bên trái để xem thông tin chi tiết.")

    def show_detail(self,item,column):
        data = item.data(0,Qt.UserRole)
        if not data: return self.show_default_detail()
        if data["type"]=="disk":
            target = self.disk_data["disks"][data["index"]]
            is_usb = "USB" in target.get("protocol","").upper()
            self.update_detail_panel(target,"disk",is_usb)
        else:
            disk = self.disk_data["disks"][data["disk_index"]]
            target = disk["volumes"][data["vol_index"]]
            self.update_detail_panel(target,"volume")

    def update_detail_panel(self,target,type_,is_usb=False):
        title = "🔌 THIẾT BỊ USB NGOÀI" if (type_=="disk" and is_usb) else ("🖴 THIẾT BỊ VẬT LÝ" if type_=="disk" else "📂 PHÂN VÙNG LOGIC")
        img_path = IMAGE_PATH_USB if (type_=="disk" and is_usb) else (IMAGE_PATH_INTERNAL if type_=="disk" else IMAGE_PATH_PARTITION)
        html = [f"<h3>{title}</h3><div style='background:#fff;padding:10px;border:1px solid #ddd;border-radius:5px;'>"]
        for k,v in target.items():
            if k in ("volumes","name"): continue
            if k in ("size_gb","free_gb"): v = f"{v:.2f} GB"
            elif k=="label" and type_=="volume": v=f"<b>{v} ({target.get('letter','')})</b>"
            html.append(f"<b>{k.replace('_',' ').capitalize()}:</b> {v}<br>")
        html.append("</div>")
        pixmap = QPixmap(img_path)
        if not pixmap.isNull(): 
            self.detail_image.setPixmap(pixmap.scaled(self.detail_image.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
            self.detail_image.setText("")
        else: 
            self.detail_image.setText("IMAGE NOT FOUND")
        self.detail_info.setText("".join(html))


# ===================== RUN APP =====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RecoverApp()
    window.show()
    sys.exit(app.exec_())
