import sys
import json
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QFrame, QApplication, QGraphicsDropShadowEffect, QMessageBox,
                             QSizePolicy, QStackedWidget)
from PyQt5.QtCore import Qt, QMargins, pyqtSignal, QEvent, QPointF
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QLinearGradient, QPalette, QBrush, QCursor, QIcon
from PyQt5.QtChart import (QChart, QChartView, QPieSeries, QPieSlice, QBarSeries, 
                           QBarSet, QBarCategoryAxis, QValueAxis, QStackedBarSeries, QAbstractBarSeries)

# --- UTILS ---
try:
    from utils import format_size
except ImportError:
    def format_size(size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024: return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"

# --- BẢNG MÀU HIỆN ĐẠI ---
MODERN_COLORS = {
    "Low": "#f87171",       # Red-400
    "Partial": "#fbbf24",   # Amber-400
    "Good": "#34d399",      # Emerald-400
    "Excellent": "#6366f1", # Indigo-500
    "Unknown": "#94a3b8"    # Slate-400
}

# --- 1. BASE CARD ---
class DashboardCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #ffffff; border-radius: 16px; border: 1px solid #e5e7eb;")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20); shadow.setColor(QColor(0, 0, 0, 30)); shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

# --- 2. FILE TYPE CARD ---
class FileTypeCard(QFrame):
    clicked = pyqtSignal(str)
    def __init__(self, category_key, title, count, size_str, c_start, c_end, icon_text):
        super().__init__()
        self.category_key = category_key; self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {c_start}, stop:1 {c_end}); border-radius: 16px; }} 
            QFrame:hover {{ margin-top: -3px; }} 
            QLabel {{ background: transparent; border: none; color: white; }}
        """)
        shadow = QGraphicsDropShadowEffect(self); shadow.setBlurRadius(15); shadow.setColor(QColor(c_start)); shadow.setOffset(0, 6); self.setGraphicsEffect(shadow)
        l = QVBoxLayout(self); l.setContentsMargins(25,25,25,25)
        icon = QLabel(icon_text); icon.setStyleSheet("font-size: 54px;"); l.addWidget(icon); l.addStretch()
        title_lbl = QLabel(title); title_lbl.setStyleSheet("font-family: 'Segoe UI'; font-size: 22px; font-weight: 800;"); l.addWidget(title_lbl)
        info = QLabel(f"{count} files • {size_str}"); info.setStyleSheet("font-family: 'Segoe UI'; font-size: 15px; font-weight: 600; color: rgba(255,255,255,220);"); l.addWidget(info)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    def mousePressEvent(self, e): 
        if e.button() == Qt.LeftButton: self.clicked.emit(self.category_key)
        super().mousePressEvent(e)

# --- 3. CHART CARD (MODERN & BIGGER) ---
class ChartCard(DashboardCard):
    def __init__(self, data_stats):
        super().__init__()
        self.data_stats = data_stats 
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # -- Header --
        header_layout = QHBoxLayout()
        title = QLabel("Độ Toàn Vẹn File")
        title.setStyleSheet("font-family: 'Segoe UI'; font-size: 20px; font-weight: 800; color: #1f2937; border: none;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.btn_switch = QPushButton("📊 Bar Chart")
        self.btn_switch.setCheckable(True)
        self.btn_switch.setCursor(Qt.PointingHandCursor)
        self.btn_switch.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9; color: #64748b; border: none; 
                border-radius: 8px; padding: 8px 12px; font-family: 'Segoe UI'; font-weight: 700; font-size: 13px;
            }
            QPushButton:hover { background-color: #e2e8f0; color: #475569; }
            QPushButton:checked { background-color: #6366f1; color: white; }
        """)
        self.btn_switch.toggled.connect(self.switch_chart)
        header_layout.addWidget(self.btn_switch)
        layout.addLayout(header_layout)

        # -- Stack --
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent; border: none;")
        
        self.pie_view = self.create_modern_pie_chart()
        self.stack.addWidget(self.pie_view)
        
        self.bar_view = self.create_modern_bar_chart()
        self.stack.addWidget(self.bar_view)
        
        layout.addWidget(self.stack)

    def switch_chart(self, checked):
        if checked:
            self.stack.setCurrentIndex(1); self.btn_switch.setText("🍩 Pie Chart")
        else:
            self.stack.setCurrentIndex(0); self.btn_switch.setText("📊 Bar Chart")

    # --- BIỂU ĐỒ TRÒN DÀY HƠN ---
    def create_modern_pie_chart(self):
        series = QPieSeries()
        # HoleSize 0.35: Bánh dày hơn
        series.setHoleSize(0.35) 
        
        total = sum(self.data_stats.values())
        categories = ["Unknown", "Low", "Partial", "Good", "Excellent"]
        
        for k in categories:
            val = self.data_stats[k]
            if val > 0:
                percent = (val / total) * 100 if total > 0 else 0
                label_text = f"{k}\n{percent:.1f}%"
                
                s = series.append(label_text, val)
                s.setBrush(QColor(MODERN_COLORS[k]))
                s.setPen(QPen(Qt.NoPen))
                
                s.setLabelVisible(True)
                s.setLabelColor(QColor("#334155")) 
                s.setLabelFont(QFont("Segoe UI", 11, QFont.Bold))
                s.setLabelArmLengthFactor(0.15) 

                if k == "Excellent": s.setExploded(True); s.setExplodeDistanceFactor(0.08)

        chart = QChart(); chart.addSeries(series)
        chart.legend().setVisible(False) 
        chart.setBackgroundBrush(QColor("transparent"))
        chart.layout().setContentsMargins(0, 0, 0, 0)
        
        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setStyleSheet("background: transparent;")
        return view

    # --- BIỂU ĐỒ CỘT DÀY & ĐẨY SỐ LÊN TRÊN ---
    def create_modern_bar_chart(self):
        categories = ["Unknown", "Low", "Partial", "Good", "Excellent"]
        
        # Dùng QStackedBarSeries để cột chiếm trọn độ rộng
        series = QStackedBarSeries()
        series.setBarWidth(0.7) 

        for i, k in enumerate(categories):
            val = self.data_stats[k]
            bar_set = QBarSet(k)
            
            # Chỉ điền giá trị tại đúng vị trí i, còn lại fill 0
            for idx in range(len(categories)):
                if idx == i: bar_set.append(val)
                else: bar_set.append(0)
            
            bar_set.setColor(QColor(MODERN_COLORS[k]))
            bar_set.setPen(QPen(Qt.NoPen)) 
            
            bar_set.setLabelFont(QFont("Segoe UI", 11, QFont.Bold))
            # FIX: Nếu giá trị > 0 thì hiện màu đen, = 0 thì trong suốt (ẩn)
            if val > 0:
                bar_set.setLabelColor(QColor("#1e293b"))
            else:
                bar_set.setLabelColor(Qt.transparent)
            
            series.append(bar_set)

        series.setLabelsFormat("@value")
        # FIX: Dùng QAbstractBarSeries.LabelsOutsideEnd để đẩy số lên đỉnh
        series.setLabelsPosition(QAbstractBarSeries.LabelsOutsideEnd)
        series.setLabelsVisible(True)

        chart = QChart(); chart.addSeries(series)
        chart.setBackgroundBrush(QColor("transparent"))
        chart.legend().setVisible(False)
        
        # Tăng lề trên để số không bị cắt
        chart.layout().setContentsMargins(0, 30, 0, 0) 

        # Trục X
        axisX = QBarCategoryAxis()
        axisX.append(categories)
        axisX.setLinePen(QPen(QColor("#e2e8f0"), 2))
        axisX.setGridLineVisible(False)
        axisX.setLabelsFont(QFont("Segoe UI", 11, QFont.DemiBold))
        axisX.setLabelsColor(QColor("#64748b"))
        chart.addAxis(axisX, Qt.AlignBottom)
        series.attachAxis(axisX)
        
        # Trục Y
        axisY = QValueAxis()
        axisY.setLinePen(QPen(Qt.NoPen))
        axisY.setGridLineVisible(False)
        axisY.setLabelsVisible(False)
        
        # Nới trần trục Y thêm 15%
        max_val = max(self.data_stats.values()) if self.data_stats else 10
        axisY.setRange(0, max_val * 1.15) 
        
        chart.addAxis(axisY, Qt.AlignLeft)
        series.attachAxis(axisY)
        
        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setStyleSheet("background: transparent;")
        return view

# --- 4. DASHBOARD WIDGET CHÍNH ---
class DashboardWidget(QWidget):
    filter_requested = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #f8fafc;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.deleted_files = self.load_data_from_file()
        self.stats = self.compute_statistics()
        self.init_ui()

    def load_data_from_file(self):
        if not os.path.exists("deleted_files.json"): return []
        try:
            with open("deleted_files.json", "r", encoding="utf-8") as f: return json.load(f)
        except: return []

    def compute_statistics(self):
        stats = {
            "total_files": len(self.deleted_files), "total_size": 0, "recoverable_high": 0,
            "completeness": {"Low": 0, "Partial": 0, "Good": 0, "Excellent": 0, "Unknown": 0},
            "types": {"Image": {"c":0,"s":0}, "Document": {"c":0,"s":0}, "Music": {"c":0,"s":0}, "Archive": {"c":0,"s":0}, "Other": {"c":0,"s":0}}
        }
        for f in self.deleted_files:
            try: f_size = int(f.get("size", 0))
            except: f_size = 0
            f_name = f.get("name", ""); f_ext = f.get("type", "").lower()
            if "." in f_name and not f_name.startswith("."): f_ext = f_name.split(".")[-1].lower()
            
            raw = str(f.get("integrity", "0"))
            if raw == "N/A": stats["completeness"]["Unknown"] += 1
            else:
                try:
                    i = float(raw)
                    if i >= 75: stats["recoverable_high"]+=1; stats["completeness"]["Excellent"]+=1
                    elif i >= 50: stats["completeness"]["Good"]+=1
                    elif i >= 25: stats["completeness"]["Partial"]+=1
                    else: stats["completeness"]["Low"]+=1
                except: stats["completeness"]["Low"]+=1
            
            stats["total_size"] += f_size
            cat = "Other"
            if f_ext in ['jpg','png','bmp','gif','webp']: cat = "Image"
            elif f_ext in ['doc','docx','pdf','txt','xls']: cat = "Document"
            elif f_ext in ['mp3','wav','flac']: cat = "Music"
            elif f_ext in ['zip','rar','7z']: cat = "Archive"
            stats["types"][cat]["c"]+=1; stats["types"][cat]["s"]+=f_size
        return stats

    def init_ui(self):
        main = QVBoxLayout(self); main.setContentsMargins(30,30,30,30); main.setSpacing(30)
        top = QHBoxLayout(); top.setSpacing(30)

        # Summary
        sum_card = DashboardCard()
        sl = QVBoxLayout(sum_card); sl.setContentsMargins(40,40,40,40)
        sl.addWidget(QLabel("TỔNG QUAN", styleSheet="color: #64748b; font: 800 16px 'Segoe UI'; border:none; letter-spacing: 1px;"))
        sl.addSpacing(10)
        sl.addWidget(QLabel(f"{self.stats['total_files']:,}", styleSheet="color: #0f172a; font: 900 68px 'Segoe UI'; border:none;"))
        sl.addWidget(QLabel("Files Found", styleSheet="color: #64748b; font: 600 18px 'Segoe UI'; border:none;"))
        sl.addSpacing(35)
        sl.addWidget(QLabel(format_size(self.stats['total_size']), styleSheet="color: #334155; font: 900 42px 'Segoe UI'; border:none;"))
        sl.addWidget(QLabel("Total Size", styleSheet="color: #64748b; font: 600 18px 'Segoe UI'; border:none;"))
        sl.addStretch()
        top.addWidget(sum_card, 1)

        # Chart
        chart_card = ChartCard(self.stats["completeness"])
        top.addWidget(chart_card, 2)
        
        # Tỷ lệ phần trên cao (75%) để chart to
        main.addLayout(top, 75) 

        # Bottom
        bot_con = QWidget(); bot = QHBoxLayout(bot_con); bot.setContentsMargins(0,0,0,0); bot.setSpacing(25)
        t = self.stats["types"]
        def add(k, tit, d, c1, c2, i):
            c = FileTypeCard(k, tit, d["c"], format_size(d["s"]), c1, c2, i)
            c.clicked.connect(self.filter_requested.emit)
            bot.addWidget(c)
        
        add("Image", "Pictures", t["Image"], "#3b82f6", "#1d4ed8", "🖼️")
        add("Document", "Documents", t["Document"], "#f43f5e", "#be123c", "📄")
        add("Archive", "Archives", t["Archive"], "#a855f7", "#7e22ce", "📦")
        add("Other", "Other", t["Other"], "#64748b", "#334155", "📁")
        
        main.addWidget(bot_con, 25)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Dữ liệu mẫu để test
    dummy = [{"name":"a.jpg","size":100,"integrity":90}]*10 + \
            [{"name":"b.doc","size":200,"integrity":60}]*5 + \
            [{"name":"c.zip","size":300,"integrity":30}]*8 + \
            [{"name":"d.txt","size":50,"integrity":10}]*3
    if not os.path.exists("deleted_files.json"):
        with open("deleted_files.json", "w") as f: json.dump(dummy, f)
    w = DashboardWidget(); w.resize(1400, 850); w.show(); sys.exit(app.exec_())