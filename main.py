# main.py (File mới)

import sys
from PyQt5.QtWidgets import QApplication
# Import từ file app_view.py đã đổi tên
from giaodien1 import RecoverApp 

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RecoverApp()
    window.show()
    sys.exit(app.exec_())