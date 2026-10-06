"""去水印工具主窗口（PyQt5）。

- 左侧：纵向滚动的阅读区，每页一个 PageView，支持自由缩放与滚动。
- 右侧：控制面板（取色 / 框选 / 容差 / 替换为色 / 选区 / 应用范围 / 视图 / 预设）。
- 全部图像处理在本地完成（core 层，纯 numpy），不联网。
"""
import os
import sys
import tempfile
import traceback as _tb

from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QMessageBox,
                             QScrollArea, QWidget, QVBoxLayout, QSplitter,
                             QLabel, QToolBar, QAction, QStatusBar, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QEvent, QSize
from PyQt5.QtGui import QKeySequence

from . import __version__
from .core.document import Doc
from .ui import icons
from .ui.page_view import PageView
from .ui.control_panel import ControlPanel
from .ui.theme import apply_theme


def _write_error_log(msg):
    """把所有异常写入系统临时目录下的 error.log，便于回传排查。"""
    try:
        log_path = os.path.join(
            tempfile.gettempdir(), 'watermark-remover-error.log')
        with open(log_path, 'a', encoding='utf-8') as f:
            import datetime as _dt
            f.write('\n==== ' + _dt.datetime.now().isoformat() + ' ====\n')
            f.write(msg + '\n')
    except Exception:
        pass


def _show_error_native(title, text):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)
    except Exception:
        pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.doc = Doc()
        self.page_views = []
        self.current = 0

        # 参数状态
        self.tool = 'pick'            # pick | roi | pan
        self.target = [200, 200, 200]
        self.tol = 40
        self.feather = 8
        self.fill = [255, 255, 255]
        self.sync_all = False
        self.view_mode = 'result'
        self.zoom = 1.0               # 相对渲染分辨率的显示倍率（1=适应宽度）

        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._apply_params)

        # 布局重排定时器：窗口/分屏真正拿到宽度后再 fit，避免初始 viewport 宽度为 0
        # 时算出的显示宽度被钳成极小值导致页面不渲染。
        self._layout_timer = QTimer()
        self._layout_timer.setSingleShot(True)
        self._layout_timer.timeout.connect(self._relayout)

        self._build_ui()
        self._install_wheel_filter()
        self.setAcceptDrops(True)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        self.setWindowTitle('Watermark Remover · 本地去水印工具')
        self.setWindowIcon(icons.make_app_icon())
        self.resize(1240, 840)
        self.setMinimumSize(860, 560)

        split = QSplitter(Qt.Horizontal)

        # 左：滚动阅读区
        self.scroll = QScrollArea()
        # True：滚动区自动让容器撑到内容高度，纵向滚动照常；
        # 若 False，容器会被钉在初始空布局尺寸(约32x32)，页面被压成 0 -> 打开后不渲染。
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.container = QWidget()
        self.container.setStyleSheet('background:#dbe0e8')
        self.vlay = QVBoxLayout(self.container)
        self.vlay.setSpacing(20)
        self.vlay.setContentsMargins(18, 18, 18, 18)
        self.vlay.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.container)

        # 右：控制面板
        self.panel = ControlPanel(self)
        # 面板参数变化 -> 去抖后重处理（拖动滑块不卡）
        self.panel.paramsChanged.connect(lambda: self._debounce.start(120))

        split.addWidget(self.scroll)
        split.addWidget(self.panel)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        split.setSizes([900, 320])
        self.setCentralWidget(split)

        self._build_toolbar()
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage('点击「打开」或把文件拖拽到窗口，即可开始')

        ver = QLabel(f'v{__version__} · 本地处理 · 不联网')
        self.statusBar().addPermanentWidget(ver)

    def _build_toolbar(self):
        tb = QToolBar('主工具栏')
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        def act(text, icon, tip, cb, shortcut=None):
            a = QAction(icon, text, self)
            a.setToolTip(tip)
            a.triggered.connect(cb)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            tb.addAction(a)
            return a

        act('打开', icons.open_icon(), '打开 PDF 或图片 (Ctrl+O)',
            self.open_file, 'Ctrl+O')

        tb.addSeparator()
        act('放大', icons.zoom_in_icon(), '放大 (Ctrl+=)', lambda: self.zoom_by(1.2), 'Ctrl+=')
        act('缩小', icons.zoom_out_icon(), '缩小 (Ctrl+-)', lambda: self.zoom_by(1 / 1.2), 'Ctrl+-')
        act('适应宽度', icons.fit_width_icon(), '适应宽度 (Ctrl+0)', self.fit_width, 'Ctrl+0')
        act('实际大小', icons.actual_size_icon(), '实际大小 (Ctrl+1)', self.actual_size, 'Ctrl+1')

        self.zoom_label = QLabel('100%')
        self.zoom_label.setObjectName('badge')
        self.zoom_label.setMinimumWidth(48)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        tb.addWidget(self.zoom_label)

        # 弹性占位：把页码指示推到工具栏右侧
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        self.page_label = QLabel('')
        self.page_label.setObjectName('badge')
        tb.addWidget(self.page_label)

    def _install_wheel_filter(self):
        self.scroll.viewport().installEventFilter(self)

    def resizeEvent(self, ev):
        """窗口/分屏尺寸变化后，延后重排页面（让页面宽度跟随阅读区宽度）。"""
        super().resizeEvent(ev)
        if self.page_views:
            self._layout_timer.start(50)

    def eventFilter(self, obj, event):
        if obj is self.scroll.viewport() and event.type() == QEvent.Wheel:
            if event.modifiers() & Qt.ControlModifier:
                delta = event.angleDelta().y()
                self.zoom_by(1.1 if delta > 0 else 1 / 1.1)
                return True  # 吃掉事件，避免同时滚动
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------- 文件
    def open_file(self):
        """通过「打开」按钮选择文件（QFileDialog）。"""
        path, _ = QFileDialog.getOpenFileName(
            self, '打开文件', '',
            '文档 (*.pdf *.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff)')
        if path:
            self.open_path(path)

    def open_path(self, path):
        """真正加载文件（按钮/拖拽/命令行 共用）。返回是否成功。"""
        try:
            if not os.path.isfile(path):
                raise FileNotFoundError('文件不存在：' + path)
            ext = os.path.splitext(path)[1].lower()
            if ext == '.pdf':
                self.doc.load_pdf(path)
            else:
                self.doc.load_image(path)
        except Exception:
            tb = _tb.format_exc()
            _write_error_log('[open_path] ' + tb)
            QMessageBox.critical(
                self, '打开失败',
                f'无法读取文件：\n{path}\n\n{tb}\n\n'
                f'（详细错误已保存到系统临时目录 watermark-remover-error.log）')
            return False
        self.current = 0
        self._build_pages()
        # 延后到事件循环空闲再 fit：此时分屏/滚动区已拿到真实宽度。
        self._layout_timer.start(0)
        self.statusBar().showMessage(
            f'已打开：{os.path.basename(path)}（共 {len(self.doc.pages)} 页）'
            f'—— 选「取色」后点一下水印颜色即可开始')
        return True

    # 拖拽文件到窗口即可加载
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            p = url.toLocalFile()
            if p:
                self.open_path(p)
                break
        e.acceptProposedAction()

    def _build_pages(self):
        # 清空旧页
        for pv in self.page_views:
            pv.deleteLater()
        self.page_views = []
        while self.vlay.count():
            item = self.vlay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for i, page in enumerate(self.doc.pages):
            pv = PageView(page, i, self)
            pv.colorPicked.connect(self._on_color_picked)
            pv.roiChanged.connect(self._on_roi_changed)
            pv.clicked.connect(self._on_page_clicked)
            self.page_views.append(pv)
            self.vlay.addWidget(pv)

    # ------------------------------------------------------------- 缩放
    def _relayout(self):
        vw = self.scroll.viewport().width() - 36
        if vw < 50:
            vw = 50
        for pv in self.page_views:
            pv.set_display_width(int(vw * self.zoom))
        pct = int(self.zoom * 100)
        self.zoom_label.setText(f'{pct}%')
        self._update_page_label()

    def zoom_by(self, f):
        self.zoom = max(0.1, min(8.0, self.zoom * f))
        self._relayout()

    def fit_width(self):
        self.zoom = 1.0
        self._relayout()

    def actual_size(self):
        # 渲染倍率 RENDER_SCALE=2，回到原始尺寸需 zoom=1/2
        self.zoom = 1.0 / 2.0
        self._relayout()

    def _update_page_label(self):
        if self.doc.pages:
            self.page_label.setText(
                f'第 {self.current + 1}/{len(self.doc.pages)} 页')
        else:
            self.page_label.setText('')

    # ------------------------------------------------- 参数 / 处理联动
    def set_tool(self, t):
        self.tool = t

    def set_view_mode(self, m):
        self.view_mode = m
        for pv in self.page_views:
            pv.view_mode = m
            pv.update()

    def set_target(self, c):
        self.target = [c[0], c[1], c[2]]

    def set_fill(self, c):
        self.fill = [c[0], c[1], c[2]]

    def set_tol(self, v):
        self.tol = v

    def set_feather(self, v):
        self.feather = v

    def set_sync_all(self, on):
        self.sync_all = on

    def _on_color_picked(self, c):
        self.target = [c[0], c[1], c[2]]
        self.panel.set_target_swatch(c)
        self.panel.paramsChanged.emit()

    def _on_roi_changed(self, roi):
        if roi is None:
            self.panel.set_roi_label('整页')
        else:
            self.panel.set_roi_label(
                f'选区 ({roi[0]},{roi[1]})→({roi[2]},{roi[3]})')
        self._debounce.start(60)

    def _on_page_clicked(self, idx):
        self.current = idx
        self._update_page_label()

    def _apply_params(self):
        if not self.doc.pages:
            return
        if self.sync_all:
            changed = self.doc.process_all(
                self.target, self.tol, self.feather, self.fill, use_roi=True)
            for pv in self.page_views:
                pv.refresh()
            self.statusBar().showMessage(
                f'已按相同规则处理全部页，共替换 {changed} 像素')
        else:
            changed = self.doc.process_page(
                self.current, self.target, self.tol, self.feather,
                self.fill, use_roi=True)
            if 0 <= self.current < len(self.page_views):
                self.page_views[self.current].refresh()
            self.statusBar().showMessage(
                f'当前页替换 {changed} 像素')

    def process_all_pages(self):
        if not self.doc.pages:
            return
        changed = self.doc.process_all(
            self.target, self.tol, self.feather, self.fill, use_roi=True)
        for pv in self.page_views:
            pv.refresh()
        self.statusBar().showMessage(
            f'已处理全部页，共替换 {changed} 像素')

    def restore_current(self):
        if not self.doc.pages:
            return
        self.doc.restore_page(self.current)
        if 0 <= self.current < len(self.page_views):
            self.page_views[self.current].refresh()
        self.statusBar().showMessage('已还原当前页')

    def restore_all(self):
        if not self.doc.pages:
            return
        self.doc.restore_all()
        for pv in self.page_views:
            pv.refresh()
        self.statusBar().showMessage('已还原全部页')

    def clear_roi(self):
        if not self.doc.pages:
            return
        if self.sync_all:
            for pg in self.doc.pages:
                pg.roi = None
        else:
            self.doc.pages[self.current].roi = None
        self.panel.set_roi_label('整页')
        self._debounce.start(60)

    def auto_light(self):
        self.target = [225, 225, 225]
        self.tol = 45
        self.feather = 8
        # 同步面板控件
        self.panel.set_target_swatch(self.target)
        self.panel.tol.setValue(45)
        self.panel.feather.setValue(8)
        self.panel.paramsChanged.emit()
        self.statusBar().showMessage('已套用「浅灰水印」预设，可微调容差')

    # ------------------------------------------------------------- 导出
    def export_png(self):
        if not self.doc.pages:
            QMessageBox.information(self, '提示', '请先打开文件')
            return
        path, _ = QFileDialog.getSaveFileName(
            self, '导出当前页 PNG', 'page.png', 'PNG (*.png)')
        if not path:
            return
        try:
            self.doc.pages[self.current].res_qimg.save(path)
            self.statusBar().showMessage(f'已导出：{path}')
        except Exception as e:
            QMessageBox.critical(self, '导出失败', repr(e))

    def export_pdf(self):
        if not self.doc.pages:
            QMessageBox.information(self, '提示', '请先打开文件')
            return
        path, _ = QFileDialog.getSaveFileName(
            self, '导出 PDF', 'output.pdf', 'PDF (*.pdf)')
        if not path:
            return
        try:
            self.doc.export_pdf(
                path, self.target, self.tol, self.feather, self.fill,
                process_all=True)
            self.statusBar().showMessage(f'已导出：{path}')
        except Exception as e:
            QMessageBox.critical(self, '导出失败', repr(e))

    # ------------------------------------------------------------- 关闭
    def closeEvent(self, ev):
        self.doc.close()
        super().closeEvent(ev)


def _global_excepthook(etype, exc, tb):
    """事件循环中未捕获的异常 -> 原生错误框 + 临时目录 error.log（避免静默崩溃）。"""
    msg = ''.join(_tb.format_exception(etype, exc, tb))
    _write_error_log('[excepthook] ' + msg)
    _show_error_native(
        'Watermark Remover - 运行错误',
        '程序运行出错（详细已保存到系统临时目录 watermark-remover-error.log）：\n\n' + msg)
    sys.__excepthook__(etype, exc, tb)


def main(argv=None):
    if argv is None:
        argv = sys.argv
    sys.excepthook = _global_excepthook

    # 在创建 QApplication 之前设置高 DPI 属性，
    # 避免高分屏下界面/图像缩放异常。
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(argv)
    app.setApplicationName('Watermark Remover')
    app.setApplicationDisplayName('Watermark Remover')
    apply_theme(app)
    app.setWindowIcon(icons.make_app_icon())

    file_to_open = argv[1] if len(argv) > 1 else None
    win = MainWindow()
    win.show()
    if file_to_open:
        # 延后到事件循环启动后再打开，确保窗口已就绪
        QTimer.singleShot(0, lambda: win.open_path(file_to_open))
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
