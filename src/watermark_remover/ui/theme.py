"""全局视觉主题：配色 + QSS 样式表。

统一在这里维护颜色与控件样式，界面代码只引用 PALETTE，不再散落魔法色值。
"""
from PyQt5.QtGui import QColor, QFont, QPalette

# ---- 调色板（浅色 · 蓝色强调） ----
PALETTE = {
    'bg':          '#f3f4f6',   # 窗口底色
    'canvas':      '#dbe0e8',   # 页面画布（阅读区）底色
    'card':        '#ffffff',   # 卡片背景
    'border':      '#e5e7eb',   # 常规描边
    'text':        '#1f2937',   # 主文字
    'text_sub':    '#6b7280',   # 次要文字
    'accent':      '#2563eb',   # 强调色
    'accent_hover': '#1d4ed8',
    'accent_soft': '#eff6ff',   # 强调色浅底
    'danger':      '#dc2626',
    'danger_soft': '#fef2f2',
}


def apply_theme(app):
    """设置应用字体、调色与全局 QSS。在创建 QApplication 之后调用。"""
    app.setFont(QFont('Microsoft YaHei UI', 9))

    pal = app.palette()
    pal.setColor(QPalette.Window, QColor(PALETTE['bg']))
    pal.setColor(QPalette.WindowText, QColor(PALETTE['text']))
    pal.setColor(QPalette.Base, QColor(PALETTE['card']))
    pal.setColor(QPalette.Text, QColor(PALETTE['text']))
    pal.setColor(QPalette.ButtonText, QColor(PALETTE['text']))
    pal.setColor(QPalette.Highlight, QColor(PALETTE['accent']))
    app.setPalette(pal)
    app.setStyleSheet(build_stylesheet())


def build_stylesheet():
    p = PALETTE
    return f"""
/* ---------- 基础 ---------- */
* {{
    font-family: "Microsoft YaHei UI", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {p['text']};
    selection-background-color: {p['accent']};
    selection-color: #ffffff;
}}
QMainWindow, QDialog {{ background: {p['bg']}; }}

/* ---------- 工具栏 ---------- */
QToolBar {{
    background: {p['card']};
    border: none;
    border-bottom: 1px solid {p['border']};
    padding: 5px 10px;
    spacing: 4px;
}}
QToolButton {{
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 5px 10px;
    color: #374151;
}}
QToolButton:hover {{ background: #eef2f7; }}
QToolButton:pressed {{ background: #e3e9f2; }}

/* ---------- 按钮 ---------- */
QPushButton {{
    background: {p['card']};
    border: 1px solid #d1d5db;
    border-radius: 7px;
    padding: 6px 12px;
    color: #374151;
}}
QPushButton:hover {{ border-color: {p['accent']}; color: {p['accent']}; background: #f8faff; }}
QPushButton:pressed {{ background: {p['accent_soft']}; }}
QPushButton:disabled {{ color: #9ca3af; border-color: {p['border']}; background: {p['bg']}; }}

QPushButton[role="primary"] {{
    background: {p['accent']};
    border: 1px solid {p['accent']};
    color: #ffffff;
    font-weight: 600;
}}
QPushButton[role="primary"]:hover {{ background: {p['accent_hover']}; border-color: {p['accent_hover']}; }}
QPushButton[role="primary"]:pressed {{ background: #1e40af; }}

QPushButton[role="danger"] {{
    background: {p['card']};
    border: 1px solid #fecaca;
    color: {p['danger']};
}}
QPushButton[role="danger"]:hover {{ background: {p['danger_soft']}; border-color: {p['danger']}; }}

/* ---------- 卡片（GroupBox） ---------- */
QGroupBox {{
    background: {p['card']};
    border: 1px solid {p['border']};
    border-radius: 10px;
    margin-top: 20px;
    padding: 8px 10px 10px 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 6px;
    top: 2px;
    padding: 0 2px;
    color: {p['text_sub']};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}}

/* ---------- 滑杆 ---------- */
QSlider::groove:horizontal {{
    height: 4px;
    background: {p['border']};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{ background: {p['accent']}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    background: #ffffff;
    border: 2px solid {p['accent']};
}}
QSlider::handle:horizontal:hover {{ border-color: {p['accent_hover']}; }}

/* ---------- 单选 / 复选 ---------- */
QRadioButton, QCheckBox {{ spacing: 8px; background: transparent; }}
QRadioButton::indicator {{
    width: 16px; height: 16px;
    border: 2px solid #d1d5db; border-radius: 8px;
    background: #ffffff;
}}
QRadioButton::indicator:hover {{ border-color: #93c5fd; }}
QRadioButton::indicator:checked {{ border: 5px solid {p['accent']}; background: #ffffff; }}

QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 2px solid #d1d5db; border-radius: 4px;
    background: #ffffff;
}}
QCheckBox::indicator:hover {{ border-color: #93c5fd; }}
QCheckBox::indicator:checked {{ background: {p['accent']}; border-color: {p['accent']}; }}

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #c3cad6; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #a7b0c0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #c3cad6; border-radius: 3px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: #a7b0c0; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---------- 状态栏 / 分割器 / 滚动区 ---------- */
QStatusBar {{
    background: {p['card']};
    border-top: 1px solid {p['border']};
    color: {p['text_sub']};
}}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ color: {p['text_sub']}; padding: 0 6px; }}
QSplitter::handle {{ background: {p['bg']}; }}
QSplitter::handle:horizontal {{ width: 3px; }}
QSplitter::handle:hover {{ background: #bfdbfe; }}
QScrollArea {{ border: none; background: transparent; }}

/* ---------- 徽标（缩放比例 / 页码） ---------- */
QLabel#badge {{
    background: {p['accent_soft']};
    color: {p['accent']};
    border-radius: 9px;
    padding: 2px 10px;
    font-weight: 600;
    font-size: 12px;
}}
QLabel#valueBadge {{
    background: {p['accent_soft']};
    color: {p['accent']};
    border-radius: 8px;
    padding: 1px 8px;
    font-weight: 700;
    font-size: 12px;
}}

/* ---------- 提示文字 ---------- */
QLabel#hint {{
    color: {p['text_sub']};
    font-size: 12px;
}}
"""
