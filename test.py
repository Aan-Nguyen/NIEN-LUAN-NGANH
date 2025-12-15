import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QTreeWidget, QHeaderView, QSplitter,
    QLabel
)
from PyQt5.QtCore import Qt, QSize
# Các lớp liên quan đến đồ họa cơ bản vẫn ở đây
from PyQt5.QtGui import QColor, QPainter, QFont

# CHUYỂN QGraphicsDropShadowEffect sang QtWidgets
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
# --- 1. Custom QGraphicsEffect (Hiệu ứng Đổ bóng tùy chỉnh) ---
class DropShadowEffect(QGraphicsDropShadowEffect):
    """
    Hiệu ứng đổ bóng tùy chỉnh với màu sắc, độ mờ và offset xác định.
    Sử dụng để tạo vẻ ngoài 'nổi' (elevated) cho widget theo phong cách hiện đại.
    """
    def __init__(self, color=QColor(0, 0, 0, 80), blur_radius=20, x_offset=0, y_offset=6):
        super().__init__()
        self.setBlurRadius(blur_radius)
        self.setColor(color)
        self.setOffset(x_offset, y_offset)

# --- 2. QSS Hiện đại (Đã chỉnh sửa để dễ dùng hơn) ---
def get_app_stylesheet():
    """Trả về chuỗi QSS cho giao diện hiện đại."""
    return """
    QWidget {
        background-color: #f5f7fa;
        font-family: 'Segoe UI', 'Roboto';
        font-size: 11pt;
        color: #2d3436;
    }

    /* Sidebar */
    #sidebar {
        background-color: #edf0f5;
        border-right: 1px solid #d6dae0;
    }

    QListWidget {
        background: transparent;
        border: none;
        font-size: 11pt;
    }

    QListWidget::item {
        padding: 12px 16px;
        border-radius: 8px;
        background: transparent;
    }

    QListWidget::item:selected {
        background-color: #d0e2ff;
        color: #0b5394;
        font-weight: 600;
    }

    QListWidget::item:hover {
        background-color: #e7edf7;
    }

    /* Tree View Container */
    #diskTreeContainer { /* Áp dụng đổ bóng/border cho container nếu cần */
        background-color: #ffffff;
        border-radius: 10px;
        /* Border bị loại bỏ ở đây để đổ bóng có thể hoạt động tốt hơn,
           hoặc di chuyển border vào TreeWidget nếu không áp dụng đổ bóng cho container. */
        padding: 0px; 
    }

    QTreeWidget {
        background-color: transparent;
        border: none; /* Border bị loại bỏ vì container đã có */
        padding: 4px;
    }

    QTreeWidget::item {
        padding-top: 6px;
        padding-bottom: 6px;
    }

    QHeaderView::section {
        background-color: #f0f3f8;
        padding: 8px;
        border: none;
        font-weight: 600;
        color: #4b5563;
    }

    /* Nút bấm */
    #scanBtn, #resetBtn {
        padding: 9px 18px;
        border-radius: 8px;
        color: white;
        font-weight: 600;
        border: none;
    }

    #scanBtn {
        background-color: #0078d7;
    }

    #scanBtn:hover {
        background-color: #005fa3;
    }

    #resetBtn {
        background-color: #6b7280;
    }

    #resetBtn:hover {
        background-color: #4b5563;
    }

    /* Panel phải */
    #rightPanel {
        background-color: #f8fafc;
        border-left: 1px solid #d6dae0;
    }

    /* Chi tiết nội dung Container */
    #detailContentContainer {
        border: 1px solid #d8dee6;
        background-color: #ffffff;
        padding: 6px 10px;
        font-size: 12px;
        line-height: 1.4;
        border-radius: 8px;
        margin-top: 6px;
        /* Loại bỏ các thuộc tính text-formatting vì Label không hỗ trợ tốt */
    }
    
    QLabel#detailContent {
        word-wrap: break-word;
        white-space: pre-wrap;
        background-color: transparent;
        border: none;
        padding: 0;
    }

    /* Scrollbar hiện đại */
    QScrollBar:vertical {
        background: #f0f2f5;
        width: 10px;
        border-radius: 5px;
    }

    QScrollBar::handle:vertical {
        background: #cfd6e0;
        border-radius: 5px;
        min-height: 20px;
    }

    QScrollBar::handle:vertical:hover {
        background: #a9b4c4;
    }

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        background: none;
        border: none;
        height: 0px;
    }
    """

# --- 3. Ứng dụng Ví dụ (Áp dụng Effect và QSS) ---
class ModernApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ứng dụng Phong cách Hiện đại với QGraphicsEffect")
        self.setGeometry(100, 100, 1000, 600)
        
        # Áp dụng StyleSheet
        self.setStyleSheet(get_app_stylesheet())

        # Widget trung tâm
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Layout tổng thể (QHBoxLayout cho Sidebar và Main Content)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Splitter để chia Sidebar và Main Content
        splitter = QSplitter(Qt.Horizontal)
        splitter.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(splitter)

        # --- Sidebar (Left Panel) ---
        sidebar_widget = QWidget()
        sidebar_widget.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar_widget)
        
        list_widget = QListWidget()
        list_widget.addItem("Trang chủ")
        list_widget.addItem("Cài đặt")
        list_widget.addItem("Lịch sử")
        list_widget.setMinimumWidth(200)
        sidebar_layout.addWidget(list_widget)
        
        # Thêm Sidebar vào Splitter
        splitter.addWidget(sidebar_widget)

        # --- Main Content (Right Panel) ---
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 15, 15, 15)

        # 1. Khu vực Nút bấm
        button_layout = QHBoxLayout()
        scan_btn = QPushButton("Quét Ngay")
        scan_btn.setObjectName("scanBtn")
        reset_btn = QPushButton("Đặt lại")
        reset_btn.setObjectName("resetBtn")
        
        # ÁP DỤNG QGraphicsEffect CHO NÚT BẤM
        scan_btn.setGraphicsEffect(DropShadowEffect(blur_radius=10, y_offset=4, color=QColor(0, 120, 215, 100)))
        reset_btn.setGraphicsEffect(DropShadowEffect(blur_radius=10, y_offset=4, color=QColor(107, 114, 128, 100)))

        button_layout.addWidget(scan_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        right_layout.addLayout(button_layout)

        # 2. Khu vực TreeView (Disk Tree)
        tree_container = QWidget()
        tree_container.setObjectName("diskTreeContainer")
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        
        disk_tree = QTreeWidget()
        disk_tree.setObjectName("diskTree") # QSS áp dụng cho QTreeWidget
        disk_tree.setHeaderLabels(["Tên tập tin", "Kích thước", "Ngày tạo"])
        disk_tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # Thêm dữ liệu giả lập
        item1 = QTreeWidgetItem(disk_tree, ["Tài liệu.docx", "1.2 MB", "10/11/2025"])
        QTreeWidgetItem(item1, ["Tóm tắt.txt", "12 KB", "09/11/2025"])
        QTreeWidgetItem(disk_tree, ["Ảnh.jpg", "4.5 MB", "01/11/2025"])
        
        tree_layout.addWidget(disk_tree)
        
        # ÁP DỤNG QGraphicsEffect CHO CONTAINER CỦA TREE VIEW
        tree_container.setGraphicsEffect(DropShadowEffect(blur_radius=15, y_offset=8, color=QColor(0, 0, 0, 40)))

        right_layout.addWidget(tree_container, 2) # Tăng tỷ lệ cho TreeView

        # 3. Khu vực Chi tiết nội dung
        detail_container = QWidget()
        detail_container.setObjectName("detailContentContainer")
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(10, 10, 10, 10)
        
        detail_label = QLabel(
            "Chi tiết nội dung của mục được chọn sẽ hiển thị ở đây. "
            "Đây là một khối text dài mô phỏng nội dung chi tiết:\n\n"
            "Tên: Tài liệu.docx\n"
            "Đường dẫn: C:\\Users\\User\\Documents\\...\n"
            "Trạng thái: Đã kiểm tra."
        )
        detail_label.setObjectName("detailContent")
        detail_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        detail_layout.addWidget(detail_label)
        
        # ÁP DỤNG QGraphicsEffect CHO CONTAINER CỦA CHI TIẾT NỘI DUNG
        detail_container.setGraphicsEffect(DropShadowEffect(blur_radius=15, y_offset=8, color=QColor(0, 0, 0, 40)))

        right_layout.addWidget(detail_container, 1) # Giảm tỷ lệ
        
        # Thêm Main Content vào Splitter
        splitter.addWidget(right_panel)
        
        # Đặt kích thước ban đầu cho splitter
        splitter.setSizes([200, 800])
        
        # Đảm bảo các widget được hiển thị đúng
        sidebar_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Bỏ qua DPI scaling cho các hệ thống HiDPI nếu cần thiết
    # app.setAttribute(Qt.AA_EnableHighDpiScaling) 
    
    from PyQt5.QtWidgets import QTreeWidgetItem, QSizePolicy # Import ở đây để tránh circular dependency
    
    window = ModernApp()
    window.show()
    sys.exit(app.exec_())