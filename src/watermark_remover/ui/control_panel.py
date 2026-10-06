"""右侧控制面板（卡片式，可纵向滚动）。

所有参数与动作都通过信号/回调与 MainWindow 联动：
- 容差 / 柔化 / 目标色 / 填充色 变化 -> 发射 paramsChanged（MainWindow 负责重处理）
- 工具、视图模式 -> 直接调用 main.set_tool / main.set_view_mode
- 处理全部 / 还原 / 清除选区 / 预设 -> 调用 main 的对应方法
"""
from PyQt5.QtWidgets import (QScrollArea, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QSlider, QRadioButton,
                             QButtonGroup, QColorDialog, QCheckBox, QGroupBox,
                             QFrame)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor

from . import icons


class _Swatch(QPushButton):
    """显示当前颜色并可点击打开取色器的小方块按钮。"""

    def __init__(self, color=(255, 255, 255)):
        super().__init__()
        self._color = color
        self.setFixedSize(52, 24)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip('点击自定义颜色')
        self._paint()

    def _paint(self):
        r, g, b = self._color
        self.setStyleSheet(
            f"QPushButton{{background-color:rgb({r},{g},{b});"
            f"border:1px solid rgba(0,0,0,0.18);border-radius:5px;}}"
            f"QPushButton:hover{{border:2px solid #2563eb;}}")

    @property
    def color(self):
        return self._color

    def set_color(self, c):
        self._color = (c[0], c[1], c[2])
        self._paint()


def _hex(c):
    return '#{:02x}{:02x}{:02x}'.format(*c).upper()


class ControlPanel(QScrollArea):
    paramsChanged = pyqtSignal()

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMinimumWidth(292)

        body = QWidget()
        self.setWidget(body)
        root = QVBoxLayout(body)
        root.setContentsMargins(12, 4, 12, 12)
        root.setSpacing(12)
        root.setAlignment(Qt.AlignTop)

        self._build_file_card(root)
        self._build_mode_card(root)
        self._build_color_card(root)
        self._build_range_card(root)
        self._build_roi_card(root)
        self._build_apply_card(root)
        self._build_view_card(root)
        self._build_preset_card(root)
        root.addStretch(1)

    # ------------------------------------------------------------ 构建辅助
    @staticmethod
    def _card(title):
        g = QGroupBox(title)
        v = QVBoxLayout(g)
        v.setContentsMargins(10, 4, 10, 10)
        v.setSpacing(8)
        return g, v

    @staticmethod
    def _btn(text, cb=None, role=None):
        b = QPushButton(text)
        b.setCursor(Qt.PointingHandCursor)
        b.setFixedHeight(31)
        if role:
            b.setProperty('role', role)
        if cb:
            b.clicked.connect(cb)
        return b

    def _slider_row(self, label, lo, hi, val, cb):
        """「名称 + 数值徽标 + 滑杆」一行的容器。返回 (容器, 滑杆)。"""
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        head = QHBoxLayout()
        head.addWidget(QLabel(label))
        head.addStretch(1)
        badge = QLabel(str(val))
        badge.setObjectName('valueBadge')
        head.addWidget(badge)

        s = QSlider(Qt.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        s.setCursor(Qt.PointingHandCursor)

        def on_change(x):
            badge.setText(str(x))
            cb(x)

        s.valueChanged.connect(on_change)
        v.addLayout(head)
        v.addWidget(s)
        return w, s

    # ------------------------------------------------------------ 各卡片
    def _build_file_card(self, root):
        g, v = self._card('文件')
        b_open = self._btn('打开 PDF / 图片', self.main.open_file, role='primary')
        b_open.setIcon(icons.open_icon(color='#ffffff'))
        b_png = self._btn('导出当前页 PNG', self.main.export_png)
        b_pdf = self._btn('导出 PDF（全部页）', self.main.export_pdf)
        for b in (b_open, b_png, b_pdf):
            v.addWidget(b)
        root.addWidget(g)

    def _build_mode_card(self, root):
        g, v = self._card('操作模式')
        self.tool_bg = QButtonGroup(self)
        for txt, val in (('取色（点选水印）', 'pick'),
                         ('框选范围', 'roi'),
                         ('平移浏览', 'pan')):
            rb = QRadioButton(txt)
            rb.setProperty('val', val)
            rb.setCursor(Qt.PointingHandCursor)
            self.tool_bg.addButton(rb)
            v.addWidget(rb)
            rb.toggled.connect(
                lambda checked, vv=val: self.main.set_tool(vv) if checked else None)
        self.tool_bg.buttons()[0].setChecked(True)
        root.addWidget(g)

    def _build_color_card(self, root):
        g, v = self._card('颜色')
        hint = QLabel('选「取色」后在页面上点一下水印，即可拾取目标色')
        hint.setObjectName('hint')
        hint.setWordWrap(True)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel('目标色'))
        row1.addStretch(1)
        self.target_hex = QLabel('#C8C8C8')
        self.target_hex.setObjectName('hint')
        row1.addWidget(self.target_hex)
        self.target_sw = _Swatch((200, 200, 200))
        self.target_sw.clicked.connect(
            lambda: self._pick_color(self.target_sw, self._on_target))
        row1.addWidget(self.target_sw)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel('替换为'))
        row2.addStretch(1)
        self.fill_hex = QLabel('#FFFFFF')
        self.fill_hex.setObjectName('hint')
        row2.addWidget(self.fill_hex)
        self.fill_sw = _Swatch((255, 255, 255))
        self.fill_sw.clicked.connect(
            lambda: self._pick_color(self.fill_sw, self._on_fill))
        row2.addWidget(self.fill_sw)

        v.addWidget(hint)
        v.addLayout(row1)
        v.addLayout(row2)
        root.addWidget(g)

    def _build_range_card(self, root):
        g, v = self._card('范围与边缘')
        w_tol, self.tol = self._slider_row('容差', 0, 150, 40, self._on_tol)
        w_fea, self.feather = self._slider_row('边缘柔化', 0, 60, 8, self._on_feather)
        v.addWidget(w_tol)
        v.addWidget(w_fea)
        root.addWidget(g)

    def _build_roi_card(self, root):
        g, v = self._card('选区')
        self.roi_lbl = QLabel('当前：整页')
        self.roi_lbl.setObjectName('hint')
        b_clear = self._btn('清除选区', self.main.clear_roi)
        v.addWidget(self.roi_lbl)
        v.addWidget(b_clear)
        root.addWidget(g)

    def _build_apply_card(self, root):
        g, v = self._card('应用范围')
        self.sync_all = QCheckBox('改动时同步到所有页')
        self.sync_all.setCursor(Qt.PointingHandCursor)
        self.sync_all.toggled.connect(self.main.set_sync_all)
        b_all = self._btn('处理全部页', self.main.process_all_pages)
        b_res = self._btn('还原当前页', self.main.restore_current, role='danger')
        b_resall = self._btn('还原全部', self.main.restore_all, role='danger')
        v.addWidget(self.sync_all)
        v.addWidget(b_all)
        row = QHBoxLayout()
        row.addWidget(b_res)
        row.addWidget(b_resall)
        v.addLayout(row)
        root.addWidget(g)

    def _build_view_card(self, root):
        g, v = self._card('视图')
        self.view_bg = QButtonGroup(self)
        for txt, val in (('去水印后', 'result'),
                         ('原图', 'original'),
                         ('对比（拖动分割线）', 'compare')):
            rb = QRadioButton(txt)
            rb.setProperty('val', val)
            rb.setCursor(Qt.PointingHandCursor)
            self.view_bg.addButton(rb)
            v.addWidget(rb)
            rb.toggled.connect(
                lambda checked, vv=val:
                self.main.set_view_mode(vv) if checked else None)
        self.view_bg.buttons()[0].setChecked(True)
        root.addWidget(g)

    def _build_preset_card(self, root):
        g, v = self._card('快速预设')
        b_auto = self._btn('一键去浅灰水印', self.main.auto_light)
        v.addWidget(b_auto)
        root.addWidget(g)

    # ------------------------------------------------------------ 颜色选择
    def _pick_color(self, swatch, cb):
        init = QColor(*swatch.color)
        c = QColorDialog.getColor(init, self, '选择颜色')
        if c.isValid():
            cb((c.red(), c.green(), c.blue()))

    def _on_target(self, c):
        self.target_sw.set_color(c)
        self.target_hex.setText(_hex(c))
        self.main.set_target(c)
        self.paramsChanged.emit()

    def _on_fill(self, c):
        self.fill_sw.set_color(c)
        self.fill_hex.setText(_hex(c))
        self.main.set_fill(c)
        self.paramsChanged.emit()

    def _on_tol(self, v):
        self.main.set_tol(v)
        self.paramsChanged.emit()

    def _on_feather(self, v):
        self.main.set_feather(v)
        self.paramsChanged.emit()

    # ------------------------------------------------------------ 外部更新
    def set_target_swatch(self, c):
        self.target_sw.set_color(c)
        self.target_hex.setText(_hex(c))

    def set_roi_label(self, text):
        self.roi_lbl.setText('当前：' + text)

    def set_sync_all(self, on):
        self.sync_all.setChecked(on)
