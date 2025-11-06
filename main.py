# main.py
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget
from giaodien1 import RecoverApp
from giaodien2 import RecoverDeletedApp
from giaodien3 import SessionManagerApp


class MainWindow(QMainWindow):
    """Controller chính quản lý chuyển đổi giữa các giao diện."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Digital Forensics Recovery Tool")
        self.resize(1150, 650)

        # Trung tâm điều khiển các trang
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # --- Khởi tạo các trang ---
        self.page_home = RecoverApp()              # Trang chính
        self.page_session = SessionManagerApp()    # Trang quản lý phiên
        self.page_scan = None                      # Trang quét (tạo động)

        # Thêm trang cố định vào stack
        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_session)

        # --- Kết nối tín hiệu ---
        self.page_home.scan_requested.connect(self.go_to_scan_page)
        self.page_home.sessions_requested.connect(self.go_to_session_page)

        self.page_session.home_requested.connect(self.go_to_home_page)
        self.page_session.session_open_requested.connect(self.open_session_scan)

        # Bắt đầu tại trang Home
        self.go_to_home_page()

    # ----------------- CHUYỂN TRANG -----------------
    def go_to_home_page(self):
        """Trở về trang Home."""
        self.stack.setCurrentWidget(self.page_home)

    def go_to_session_page(self):
        """Chuyển đến trang quản lý phiên."""
        self.page_session.load_sessions()  # Làm mới danh sách
        self.stack.setCurrentWidget(self.page_session)

    def go_to_scan_page(self, target_info, scan_type):
        """Tạo hoặc mở trang quét mới."""
        # Xóa trang cũ nếu đã tồn tại để tránh trùng widget
        if self.page_scan is not None:
            self.stack.removeWidget(self.page_scan)
            self.page_scan.deleteLater()

        self.page_scan = RecoverDeletedApp(target=target_info, scan_type=scan_type)
        self.page_scan.home_requested.connect(self.go_to_home_page)
        self.stack.addWidget(self.page_scan)
        self.stack.setCurrentWidget(self.page_scan)

    def open_session_scan(self, session_file_path):
        """Mở một phiên quét đã lưu."""
        if self.page_scan is not None:
            self.stack.removeWidget(self.page_scan)
            self.page_scan.deleteLater()

        self.page_scan = RecoverDeletedApp(session_file=session_file_path)
        self.page_scan.home_requested.connect(self.go_to_home_page)
        self.stack.addWidget(self.page_scan)
        self.stack.setCurrentWidget(self.page_scan)


# ===================== CHẠY ỨNG DỤNG =====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
