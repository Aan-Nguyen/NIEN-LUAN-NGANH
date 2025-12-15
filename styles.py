# styles.py
from PyQt5.QtGui import QColor

def get_app_stylesheet():
    """Trả về QSS hiện đại, đồng nhất cho toàn bộ ứng dụng, TỐI ƯU BẢNG VÀ CHI TIẾT."""
    return """
    QWidget {
        background-color: #f5f7fa;
        font-family: 'Segoe UI', 'Roboto';
        font-size: 11pt;
        color: #2d3436;
    }

    /* ========================================================= */
    /* ===== CÁC QUY TẮC CHUNG CHO TẤT CẢ WIDGETS (CORE) ===== */
    /* ========================================================= */

    QLabel { color: #374151; background: transparent; }

    /* Quy tắc chung cho các container Card */
    #diskTreeContainer, #tableContainer { 
        background: #ffffff;
        border-radius: 14px;
        border: 1px solid #e5e7eb;
    }

    /* Headers (Chung cho QTreeWidget và QTableWidget) */
    QHeaderView::section {
        background-color: #f9fafb;
        color: #374151;
        font-weight: bold;
        border: none;
        padding: 8px 10px; /* Tăng padding */
        border-bottom: 2px solid #e0e7ff; /* Đường kẻ dưới nhẹ */
    }

    /* QLineEdit (Hộp tìm kiếm) */
    QLineEdit {
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 8px 12px;
        background-color: #ffffff;
        selection-background-color: #d0e2ff;
    }


    /* ========================================================= */
    /* ======================= SIDEBAR (1) ======================= */
    /* ========================================================= */
    #sidebar {
        background-color: #ffffff;
        border-right: 1px solid #dfe6e9;
        border-radius: 0px;
    }

    #sidebar QPushButton {
        background-color: #f0f2f5;
        border: none;
        border-radius: 8px;
        padding: 8px 12px;
        font-weight: 500;
        color: #2d3436;
    }
    #sidebar QPushButton:hover {
        background-color: #e0e7ff;
        color: #1d4ed8;
    }
    #sidebar QPushButton:pressed {
        background-color: #c7d2fe;
    }

    /* Nút riêng (Override) */
    #scanBtn, #openSessionBtn { /* Áp dụng cho cả scanBtn và openSessionBtn */
        background-color: #2563eb;
        color: white;
        font-weight: bold;
    }
    #scanBtn:hover, #openSessionBtn:hover {
        background-color: #1e40af;
    }

    #resetBtn, #rescanBtn { /* Áp dụng cho cả resetBtn và rescanBtn */
        background-color: #f3f4f6;
        color: #374151;
    }
    #resetBtn:hover, #rescanBtn:hover {
        background-color: #e5e7eb;
    }

    #workBtn, #saveBtn { /* Áp dụng cho workBtn và saveBtn */
        background-color: #10b981;
        color: white;
    }
    #workBtn:hover, #saveBtn:hover {
        background-color: #059669;
    }
    
    #deleteSessionBtn {
        background-color: #ef4444; /* Đỏ */
        color: white;
    }
    #deleteSessionBtn:hover {
        background-color: #dc2626;
    }
    #recoverBtn {
    background-color: #2196f3;
    color: white;
    border-radius: 8px;
    padding: 8px;
    height: 40px;
    font-size: 20px;
    font-weight: bold;
    }

    #recoverBtn:hover {
        background-color: #1976d2;
    }


    /* ========================================================= */
    /* ======================= TREE VIEW (1) ======================= */
    /* ========================================================= */
    #diskTree {
        background-color: transparent;
        border: none;
        outline: none;
    }

    QTreeWidget::item {
        padding: 6px 10px;
        border-radius: 6px;
        margin: 2px;
    }
    QTreeWidget::item:selected {
        background-color: #dbeafe;
        color: #1e3a8a;
    }
    /* ========================================================= */
    /* ======================= TABLE VIEW (2 & 3) ======================= */
    /* ========================================================= */
    /* Loại bỏ viền đen khó chịu của TreeWidget */
    QTreeWidget, QTreeView {
        border: none;
        outline: none;
        background: transparent;
    }

    QTreeWidget::viewport, QTreeView::viewport {
        border: none;
        background: transparent;
    }

    QTableWidget {
        background-color: transparent;
        border: none;
        gridline-color: #e5e7eb; /* Đường kẻ bảng nhẹ */
        outline: none;
    }
    
    QTableWidget::item {
        padding: 8px 10px;
        border-bottom: 1px solid #f3f4f6;
    }
    
    QTableWidget::item:selected {
        background-color: #c7d2fe; /* Màu xanh nhẹ khi chọn */
        color: #1e3a8a;
    }
    
    QTableWidget::item:hover {
        background-color: #f7f9fc; /* Màu sáng khi hover */
    }


    /* ========================================================= */
    /* ==================== DETAIL PANEL (ALL) ===================== */
    /* ========================================================= */
    #rightPanel {
        background-color: #f8fafc; /* Nền nhẹ hơn cho panel phải */
        border-left: 1px solid #d1d5db;
    }

    #detailContentContainer {
        background-color: #ffffff;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
    }
    
    /* Image Placeholder */
    QLabel#detailImage {
        border: 1px dashed #d1d5db;
        background-color: #fafafa;
        border-radius: 8px;
        padding: 5px;
        color: #6b7280;
    }

    /* Thông tin chi tiết */
    QLabel#detailInfoLabel p { 
        font-size: 10pt;
        color: #374151;
        margin: 0;
        padding: 2px 0;
    }
    QLabel#detailInfoLabel h3 {
        margin-top: 0;
        margin-bottom: 5px;
        padding: 0;
        color: #1f2937;
    }
    
    /* Status Label (giaodien2) */
    QLabel#statusLabel {
        font-weight: 600;
        padding-top: 5px;
        color: #4b5563;
    }
    
    /* ========================================================= */
    /* ======================= SCROLLBAR (ALL) ===================== */
    /* ========================================================= */
    QScrollBar:vertical {
        border: none;
        background: #f3f4f6;
        width: 10px;
        border-radius: 5px;
        margin: 10px 0 10px 0;
    }
    QScrollBar::handle:vertical {
        background: #9ca3af;
        border-radius: 5px;
        min-height: 20px;
    }
    QScrollBar::handle:vertical:hover {
        background: #6b7280;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }

    QScrollBar:horizontal {
        height: 8px;
        background: #f3f4f6;
        border-radius: 4px;
        margin: 0 10px;
    }
    QScrollBar::handle:horizontal {
        background: #9ca3af;
        border-radius: 4px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #6b7280;
    }
    /* ====== QMessageBox ====== */
    QMessageBox {
        background-color: #ffffff;
        border: 1px solid #dfe6f1;
        border-radius: 14px;
        padding: 10px;
    }

    /* Title text */
    QMessageBox QLabel {
        color: #2d3436;
        font-family: "Segoe UI";
        font-size: 12pt;
    }

    /* Icon (warning, info...) */
    QMessageBox QLabel#qt_msgbox_label {
        font-size: 13pt;
        font-weight: 600;
        color: #2d3436;
    }

    /* Detailed text (optional) */
    QMessageBox QTextEdit {
        background-color: #f5f7fa;
        border-radius: 8px;
        border: 1px solid #e1e8f0;
        padding: 5px;
    }

    /* ====== Buttons ====== */
    QMessageBox QPushButton {
        background-color: #eaf0f9;
        color: #2d3436;
        border: 1px solid #d0d7e2;
        border-radius: 8px;
        padding: 6px 15px;
        font-family: "Segoe UI";
        font-size: 11pt;
    }

    QMessageBox QPushButton:hover {
        background-color: #dce6f5;
        border-color: #b7c5d8;
    }

    QMessageBox QPushButton:pressed {
        background-color: #c9d7ec;
        border-color: #a6b8d0;
    }

    QMessageBox QPushButton:default {
        background-color: #4c8bfd;
        color: white;
        border: none;
    }

    QMessageBox QPushButton:default:hover {
        background-color: #3a78f0;
    }

    QMessageBox QPushButton:default:pressed {
        background-color: #2f68d8;
    }
    /* ========================================================= */
/* =================== PROGRESS WINDOW ===================== */
/* ========================================================= */

/* 1. Cửa sổ chính (Thay thế cho #progressContainer cũ) */
QDialog#ScanProgressWindow {
    background-color: #ffffff;
    /* Không cần border-radius vì đây là cửa sổ hệ thống */
}

/* 2. Label Trạng thái (Thay thế cho progressTitle) */
QLabel#progressStatusLabel {
    font-weight: 600;
    color: #374151;
    font-size: 10pt;
}

/* 3. Progress bar – Giữ nguyên phong cách cũ */
QProgressBar#scanProgressBar {
    border: none;
    background-color: #f3f4f6;
    border-radius: 6px;
    height: 14px; /* Hoặc 25px tùy bạn chỉnh trong python */
    text-align: center;
    color: #374151;
    font-weight: bold;
}

QProgressBar#scanProgressBar::chunk {
    background-color: #2563eb; /* Màu xanh dương */
    border-radius: 6px;
}

/* 4. Nút Dừng – Giữ nguyên phong cách cũ */
QPushButton#btnStopScan {
    background-color: #ef4444; /* Màu đỏ */
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    font-size: 10pt;
}

QPushButton#btnStopScan:hover {
    background-color: #dc2626; /* Đỏ đậm hơn khi hover */
}

QPushButton#btnStopScan:pressed {
    background-color: #b91c1c;
    padding-top: 2px; /* Hiệu ứng nhấn */
}

QPushButton#btnStopScan:disabled {
    background-color: #9ca3af; /* Màu xám khi đã bấm dừng */
    color: #f3f4f6;
}

   """