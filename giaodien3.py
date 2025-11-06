# giaodien3.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QFrame, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import json, os, sys 
from styles import get_app_stylesheet
from datetime import datetime

class SessionManagerApp(QWidget):
    home_requested = pyqtSignal()
    session_open_requested = pyqtSignal(str) 
    def __init__(self):
        super().__init__()
        self.setStyleSheet(get_app_stylesheet())
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ===================== SIDEBAR =====================
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.setSpacing(20)

        # Tiêu đề sidebar
        sidebar_layout.addWidget(QLabel("🗂 <b>Sessions</b>", alignment=Qt.AlignCenter, font=QFont("Segoe UI", 14)))

        # Nút Home
        self.home_btn = QPushButton("🏠 Home") 
        self.home_btn.setFixedHeight(40)
        self.home_btn.clicked.connect(self.go_home) 
        sidebar_layout.addWidget(self.home_btn)

        # (SỬA) Tương tự cho open_btn
        self.open_btn = QPushButton("📂 Mở phiên") 
        self.open_btn.setFixedHeight(40)
        self.open_btn.clicked.connect(self.open_selected_session)
        sidebar_layout.addWidget(self.open_btn)

        sidebar_layout.addStretch()

        sidebar = QFrame()
        sidebar.setLayout(sidebar_layout)
        sidebar.setFixedWidth(220)
        sidebar.setObjectName("sidebar")

        # ===================== CONTENT =====================
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(25, 25, 25, 25)
        content_layout.setSpacing(15)

        title = QLabel("📁 DANH SÁCH PHIÊN LÀM VIỆC")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(title)

        # Bảng hiển thị
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Tên phiên", "Thiết bị", "Ngày lưu", "Đường dẫn"
        ])
        self.table.verticalHeader().setVisible(False)  # ❌ Ẩn cột số mặc định
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        content_layout.addWidget(self.table)

        # ===================== ADD TO MAIN =====================
        main_layout.addWidget(sidebar)
        main_layout.addLayout(content_layout)

        # Tải dữ liệu
        self.load_sessions()

    # ===================== LOAD SESSIONS =====================
    def load_sessions(self):
        self.table.setRowCount(0)
        index_path = os.path.join("sessions", "index.json")

        if not os.path.exists(index_path):
            QMessageBox.information(self, "Chưa có dữ liệu", "Chưa có phiên làm việc nào được lưu.")
            return

        try:
            with open(index_path, "r", encoding="utf-8") as f:
                sessions = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể đọc file index.json:\n{e}")
            return

        for row, sess in enumerate(sessions):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(sess.get("session_name", "Không rõ")))
            self.table.setItem(row, 1, QTableWidgetItem(sess.get("device_name", "unknown")))

            # --- Format timestamp ---
            raw_ts = sess.get("timestamp", "")
            try:
                # Nếu timestamp dạng YYYYMMDD_HHMMSS
                ts = datetime.strptime(raw_ts, "%Y%m%d_%H%M%S")
                display_ts = ts.strftime("%d/%m/%Y %H:%M:%S")
            except ValueError:
                # Nếu timestamp khác định dạng, hiển thị nguyên
                display_ts = raw_ts

            self.table.setItem(row, 2, QTableWidgetItem(display_ts))
            self.table.setItem(row, 3, QTableWidgetItem(sess.get("file_path", "")))

        self.table.resizeColumnsToContents()

    # ===================== OPEN SESSION =====================
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

        # ===================== GO HOME =====================
    def go_home(self):
        self.home_requested.emit()


# ===================== RUN APP =====================
# if __name__ == "__main__":
#     from PyQt5.QtWidgets import QApplication
#     app = QApplication(sys.argv)
#     win = SessionManagerApp()
#     win.show()
#     sys.exit(app.exec_())
