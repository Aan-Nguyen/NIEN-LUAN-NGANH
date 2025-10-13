# styles.py

def get_app_stylesheet():
    """Trả về chuỗi QSS cho ứng dụng."""
    return """
    QWidget {
        background-color: #f7f9fc;
        font-family: 'Segoe UI';
        font-size: 11pt;
    }

    #sidebar {
        background-color: #e8ecf2;
        border-right: 1px solid #c5c9cf;
    }

    QListWidget {
        background: transparent;
        border: none;
        font-size: 11pt;
    }

    /* Tăng padding cho các mục menu để làm hàng cao hơn */
    QListWidget::item {
        padding: 12px 15px; /* Tăng từ 10px lên 12px */
        border-radius: 6px;
    }

    QListWidget::item:selected {
        background-color: #d1d8e0;
        color: black;
    }

    QListWidget::item:hover {
        background-color: #dee3ea;
    }

    #diskTree {
        background-color: white;
        border: 1px solid #d0d0d0;
        border-radius: 8px;
    }

    /* Thiết lập padding cho các mục trong Tree Widget */
    /* Điều này sẽ tăng chiều cao của mỗi hàng */
    QTreeWidget::item {
        padding-top: 5px; /* Thêm đệm trên */
        padding-bottom: 5px; /* Thêm đệm dưới */
    }

    QHeaderView::section {
        background-color: #eef1f5;
        padding: 8px;
        border: none;
        font-weight: bold;
    }

    #scanBtn, #resetBtn {
        padding: 8px 15px;
        border-radius: 6px;
        color: white;
    }

    #scanBtn {
        background-color: #0078d7;
    }

    #scanBtn:hover {
        background-color: #005fa3;
    }

    #resetBtn {
        background-color: #5b5b5b;
    }

    #resetBtn:hover {
        background-color: #333;
    }

    #rightPanel {
        background-color: #f1f4f8;
        border-left: 1px solid #c5c9cf;
    }
    # styles.py

    QWidget {
        background-color: #f7f9fc;
        font-family: 'Segoe UI';
        font-size: 11pt;
    }

    #sidebar {
        background-color: #e8ecf2;
        border-right: 1px solid #c5c9cf;
    }

    QListWidget {
        background: transparent;
        border: none;
        font-size: 11pt;
    }

    QListWidget::item {
        padding: 10px 15px;
        border-radius: 6px;
    }

    QListWidget::item:selected {
        background-color: #d1d8e0;
        color: black;
    }

    QListWidget::item:hover {
        background-color: #dee3ea;
    }

    #diskTree {
        background-color: white;
        border: 1px solid #d0d0d0;
        border-radius: 8px;
    }

    QHeaderView::section {
        background-color: #eef1f5;
        padding: 8px;
        border: none;
        font-weight: bold;
    }

    #scanBtn, #resetBtn {
        padding: 8px 15px;
        border-radius: 6px;
        color: white;
    }

    #scanBtn {
        background-color: #0078d7;
    }

    #scanBtn:hover {
        background-color: #005fa3;
    }

    #resetBtn {
        background-color: #5b5b5b;
    }

    #resetBtn:hover {
        background-color: #333;
    }

    #rightPanel {
        background-color: #f1f4f8;
        border-left: 1px solid #c5c9cf;
    }
    """
