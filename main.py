import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget
from giaodien1 import RecoverApp
from giaodien2 import RecoverDeletedApp
from giaodien3 import SessionManagerApp


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Digital Forensics Recovery Tool")
        self.resize(1150, 650)

        # QStackedWidget trung tâm
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Khởi tạo trang cố định
        self.page_home = RecoverApp()
        self.page_session = SessionManagerApp()
        self.page_scan = None

        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_session)

        # Gắn tín hiệu
        self.page_home.scan_requested.connect(self.go_to_scan_page)
        self.page_home.sessions_requested.connect(self.go_to_session_page)

        self.page_session.home_requested.connect(self.go_to_home_page)
        self.page_session.session_open_requested.connect(self.open_session_scan)

        # Mặc định về Home
        self.go_to_home_page()

    # ----------------- CHUYỂN TRANG -----------------
    def go_to_home_page(self):
        self.stack.setCurrentWidget(self.page_home)

    def go_to_session_page(self):
        self.page_session.load_sessions()
        self.stack.setCurrentWidget(self.page_session)

    def go_to_scan_page(self, target_info, scan_type):
        # Xóa trang cũ an toàn
        if self.page_scan is not None:
            self.stack.setCurrentWidget(self.page_home)   # tránh nhấp nháy
            self.page_scan.setGraphicsEffect(None)
            self.page_scan.deleteLater()
            self.stack.removeWidget(self.page_scan)

        # Tạo trang quét mới
        self.page_scan = RecoverDeletedApp(target=target_info, scan_type=scan_type)
        self.page_scan.home_requested.connect(self.go_to_home_page)

        self.stack.addWidget(self.page_scan)
        self.stack.setCurrentWidget(self.page_scan)

    def open_session_scan(self, session_file_path):
        if self.page_scan is not None:
            self.stack.setCurrentWidget(self.page_home)
            self.page_scan.setGraphicsEffect(None)
            self.page_scan.deleteLater()
            self.stack.removeWidget(self.page_scan)

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
