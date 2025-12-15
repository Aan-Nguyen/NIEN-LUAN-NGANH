# giaodien3.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QFrame, QHeaderView,
    QGraphicsDropShadowEffect, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor 
import json, os, sys 
from styles import get_app_stylesheet
from datetime import datetime

# --- 1. Custom QGraphicsEffect (Hiệu ứng Đổ bóng tùy chỉnh) ---
class DropShadowEffect(QGraphicsDropShadowEffect):
    def __init__(self, color=QColor(0, 0, 0, 80), blur_radius=15, x_offset=0, y_offset=6):
        super().__init__()
        self.setBlurRadius(blur_radius)
        self.setColor(color)
        self.setOffset(x_offset, y_offset)
# -----------------------------------------------------------


class SessionManagerApp(QWidget):
    home_requested = pyqtSignal()
    session_open_requested = pyqtSignal(str) 
    def __init__(self):
        super().__init__()
        self.setStyleSheet(get_app_stylesheet())
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0) 

        # ===================== SIDEBAR =====================
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(15, 20, 15, 20) 
        sidebar_layout.setSpacing(10) # Thống nhất spacing

        # Tiêu đề sidebar
        title_label = QLabel("🗂 <b>Sessions</b>", alignment=Qt.AlignCenter)
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        sidebar_layout.addWidget(title_label)
        sidebar_layout.addSpacing(15)

        # Nút Home
        self.home_btn = QPushButton("🏠 Home") 
        self.home_btn.setObjectName("homeBtn") 
        # ÁP DỤNG EFFECT - LOẠI BỎ MÀU CỨNG
        self.home_btn.setGraphicsEffect(DropShadowEffect(blur_radius=10, y_offset=4)) 
        self.home_btn.setFixedHeight(40)
        self.home_btn.clicked.connect(self.go_home) 
        sidebar_layout.addWidget(self.home_btn)

        # Nút Mở phiên
        self.open_btn = QPushButton("📂 Mở phiên") 
        self.open_btn.setObjectName("openSessionBtn") 
        # ÁP DỤNG EFFECT - LOẠI BỎ MÀU CỨNG
        self.open_btn.setGraphicsEffect(DropShadowEffect(blur_radius=10, y_offset=4)) 
        self.open_btn.setFixedHeight(40)
        self.open_btn.clicked.connect(self.open_selected_session)
        sidebar_layout.addWidget(self.open_btn)
        
        # Nút Xóa phiên
        self.delete_btn = QPushButton("🗑 Xóa phiên")
        self.delete_btn.setObjectName("deleteSessionBtn") 
        # ÁP DỤNG EFFECT - LOẠI BỎ MÀU CỨNG
        self.delete_btn.setGraphicsEffect(DropShadowEffect(blur_radius=10, y_offset=4)) 
        self.delete_btn.setFixedHeight(40)
        self.delete_btn.clicked.connect(self.delete_selected_session)
        sidebar_layout.addWidget(self.delete_btn)

        sidebar_layout.addStretch()

        sidebar = QFrame()
        sidebar.setLayout(sidebar_layout)
        sidebar.setFixedWidth(240) 
        sidebar.setObjectName("sidebar")
        
        # Áp dụng đổ bóng mạnh hơn cho sidebar (tương tự giaodien1)
        sidebar.setGraphicsEffect(DropShadowEffect(QColor(0, 0, 0, 40), 20, 0, 8)) 

        # ===================== CONTENT =====================
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(25, 25, 25, 25)
        content_layout.setSpacing(15)

        title = QLabel("📁 DANH SÁCH PHIÊN LÀM VIỆC")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold)) 
        title.setAlignment(Qt.AlignLeft)
        content_layout.addWidget(title)
        
        # CONTAINER cho Bảng (Áp dụng Card/Shadow)
        table_container = QFrame()
        table_container.setObjectName("tableContainer") # ID cho QSS (Đã có trong styles.py)
        table_container_layout = QVBoxLayout(table_container)
        table_container_layout.setContentsMargins(0, 0, 0, 0) # QSS sẽ lo phần padding/border

        # Bảng hiển thị
        self.table = QTableWidget()
        self.table.setObjectName("sessionTable") # ID cho QSS (Đã có trong styles.py)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Tên phiên", "Thiết bị", "Ngày lưu", "Đường dẫn"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows) # Thêm thuộc tính này
        self.table.setSelectionMode(QAbstractItemView.SingleSelection) # Thêm thuộc tính này
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers) # Không cho sửa
        self.table.setSortingEnabled(True)
        
        table_container_layout.addWidget(self.table)
        
        # ÁP DỤNG DROP SHADOW cho CONTAINER BẢNG
        table_container.setGraphicsEffect(DropShadowEffect(blur_radius=20, y_offset=10, color=QColor(0, 0, 0, 30)))

        content_layout.addWidget(table_container)

        # ===================== ADD TO MAIN =====================
        main_layout.addWidget(sidebar)
        main_layout.addLayout(content_layout)

        # Tải dữ liệu
        self.load_sessions()

    # ===================== LOAD SESSIONS (GIỮ NGUYÊN LOGIC) =====================
    def load_sessions(self):
        # Tắt sắp xếp trước khi chèn hàng
        self.table.setSortingEnabled(False) 
        self.table.setRowCount(0)
        index_path = os.path.join("sessions", "index.json")

        if not os.path.exists(index_path):
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("Chưa có phiên làm việc nào được lưu."))
            self.table.setSpan(0, 0, 1, 4)
            self.table.item(0, 0).setTextAlignment(Qt.AlignCenter)
            self.table.setColumnHidden(1, True)
            self.table.setColumnHidden(2, True)
            self.table.setColumnHidden(3, True)
            self.table.setSortingEnabled(True) # Bật lại sắp xếp (dù không có dữ liệu)
            return

        # Bật lại cột
        self.table.setColumnHidden(1, False)
        self.table.setColumnHidden(2, False)
        self.table.setColumnHidden(3, False)
        
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                sessions = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể đọc file index.json:\n{e}")
            self.table.setSortingEnabled(True) # Bật lại sắp xếp
            return

        for row, sess in enumerate(sessions):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(sess.get("session_name", "Không rõ")))
            self.table.setItem(row, 1, QTableWidgetItem(sess.get("device_name", "unknown")))

            raw_ts = sess.get("timestamp", "")
            try:
                ts = datetime.strptime(raw_ts, "%Y%m%d_%H%M%S")
                display_ts = ts.strftime("%d/%m/%Y %H:%M:%S")
            except ValueError:
                display_ts = raw_ts

            self.table.setItem(row, 2, QTableWidgetItem(display_ts))
            self.table.setItem(row, 3, QTableWidgetItem(sess.get("file_path", "")))

        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True) # Bật lại sắp xếp sau khi load xong

    # ===================== DELETE SESSION (GIỮ NGUYÊN LOGIC) =====================
    def delete_selected_session(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.information(self, "Chưa chọn", "Hãy chọn một phiên để xóa.")
            return

        file_path_item = self.table.item(row, 3)
        if not file_path_item:
            QMessageBox.warning(self, "Lỗi", "Không thể xác định đường dẫn file phiên.")
            return
            
        file_path = file_path_item.text()
        
        reply = QMessageBox.question(self, 'Xác nhận xóa', 
            f"Bạn có chắc chắn muốn xóa phiên này không?:\n{os.path.basename(file_path)}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                index_path = os.path.join("sessions", "index.json")
                if os.path.exists(index_path):
                    with open(index_path, "r", encoding="utf-8") as f:
                        sessions = json.load(f)
                    
                    sessions = [sess for sess in sessions if sess.get("file_path") != file_path]
                    
                    with open(index_path, "w", encoding="utf-8") as f:
                        json.dump(sessions, f, ensure_ascii=False, indent=2)
                        
                QMessageBox.information(self, "Hoàn tất", f"Đã xóa phiên thành công.")
                self.load_sessions() 
                
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa phiên làm việc:\n{e}")

    # ===================== OPEN SESSION (GIỮ NGUYÊN LOGIC) =====================
    def open_selected_session(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.information(self, "Chưa chọn", "Hãy chọn một phiên để mở.")
            return

        file_path = self.table.item(row, 3).text()
        print("DEBUG: Trying to open session file:", file_path)

        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Không tìm thấy", f"File không tồn tại:\n{file_path}")
            return

        self.session_open_requested.emit(file_path)

    # ===================== GO HOME (GIỮ NGUYÊN LOGIC) =====================
    def go_home(self):
        self.home_requested.emit()