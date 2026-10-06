"""单页画布：负责显示、自由缩放、纵向滚动、取色、框选范围、前后对比。

每个 PageView 对应文档的一页。缩放只改变 widget 尺寸与绘制时的目标矩形，
不重新渲染位图，因此放大不卡。坐标映射固定为
  显示坐标 / 显示尺寸 * 原图像素尺寸
保证取色与框选都落在原图分辨率上。
"""
from PyQt5.QtWidgets import QWidget, QSizePolicy, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QSize, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor, QCursor, QFont, QRegion, QBrush

from .. import __version__


class PageView(QWidget):
    colorPicked = pyqtSignal(tuple)   # (r,g,b) 来自原图像素
    roiChanged = pyqtSignal(object)   # (x0,y0,x1,y1) 像素坐标 或 None
    clicked = pyqtSignal(int)         # 当前页索引，用于联动右侧面板

    def __init__(self, page, index, main):
        super().__init__()
        self.page = page
        self.index = index
        self.main = main
        self.display_scale = 1.0
        self.view_mode = 'result'     # result | original | compare
        self.compare_x = 0.5
        self._roi_disp = None         # QRect，显示坐标系
        self._drag_start = None
        self._mode = None             # 'roi' | 'divider' | 'pan'
        self._disp_w = 0              # 期望显示宽（像素），由 sizeHint 返回
        self._disp_h = 0              # 期望显示高（像素）
        # 固定尺寸策略：让 QVBoxLayout 严格按 sizeHint 给尺寸，
        # 避免布局把画布压缩成 0（这是「打开后不渲染」的根因）。
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setMouseTracking(True)

        # 页面投影：让页面在灰色画布上有悬浮感
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(15, 23, 42, 55))
        self.setGraphicsEffect(shadow)

    # ---------- 尺寸 / 缩放 ----------
    def set_display_width(self, width_px):
        """按给定显示宽度（已含 self.main.zoom）设置 widget 期望尺寸。"""
        img = self.page.res_qimg
        ow, oh = img.width(), img.height()
        if width_px <= 0:
            width_px = ow
        scale = width_px / ow
        self.display_scale = scale
        self._disp_w = int(ow * scale)
        self._disp_h = int(oh * scale)
        # 关键：通知父布局尺寸变了，否则布局仍按旧的(0,0)分配 -> 画布 0 尺寸。
        self.updateGeometry()
        self.update()

    def sizeHint(self):
        # 返回期望显示尺寸，而非当前实时 width/height（初始为 0）。
        return QSize(self._disp_w, self._disp_h)

    # ---------- 绘制 ----------
    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = self.rect()
        if self.view_mode == 'original':
            p.drawImage(rect, self.page.orig_qimg)
        elif self.view_mode == 'compare':
            p.drawImage(rect, self.page.res_qimg)
            div = int(self.compare_x * rect.width())
            p.setClipRect(0, 0, div, rect.height())
            p.drawImage(rect, self.page.orig_qimg)
            p.setClipping(False)
            pen = QPen(QColor('#2563eb'))
            pen.setWidth(2)
            p.setPen(pen)
            p.drawLine(div, 0, div, rect.height())
            self._draw_compare_badges(p, div)
        else:
            p.drawImage(rect, self.page.res_qimg)

        # ROI 选区：选区外压暗 + 蓝色虚线框
        if self._roi_disp is not None:
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(15, 23, 42, 70)))
            p.setClipRegion(QRegion(rect) - QRegion(self._roi_disp))
            p.drawRect(rect)
            p.setClipping(False)
            p.setBrush(Qt.NoBrush)
            pen = QPen(QColor('#2563eb'))
            pen.setWidth(2)
            pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            p.drawRect(self._roi_disp)

    def _draw_compare_badges(self, p, div):
        """对比模式下在左右两半顶部画「原图 / 处理后」小徽标。"""
        f = QFont('Microsoft YaHei UI', 9)
        p.setFont(f)
        fm = p.fontMetrics()

        def badge(text, right_edge):
            w = fm.horizontalAdvance(text) + 16
            h = fm.height() + 6
            x = right_edge - w
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(255, 255, 255, 215)))
            p.drawRoundedRect(QRectF(x, 10, w, h), 4, 4)
            p.setPen(QPen(QColor('#374151')))
            p.drawText(QRectF(x, 10, w, h), Qt.AlignCenter, text)

        badge('原图', div - 8)
        badge('处理后', self.width() - 8)

    # ---------- 坐标映射 ----------
    def map_to_orig(self, pos):
        img = self.page.orig_qimg
        ow, oh = img.width(), img.height()
        x = pos.x() / max(1, self.width()) * ow
        y = pos.y() / max(1, self.height()) * oh
        return (int(max(0, min(ow - 1, x))), int(max(0, min(oh - 1, y))))

    # ---------- 鼠标交互 ----------
    def mousePressEvent(self, ev):
        self.clicked.emit(self.index)
        if ev.button() != Qt.LeftButton:
            return
        if self.view_mode == 'compare':
            self._mode = 'divider'
            self.compare_x = max(0.0, min(1.0, ev.pos().x() / max(1, self.width())))
            self.update()
            return
        tool = self.main.tool
        if tool == 'pick':
            x, y = self.map_to_orig(ev.pos())
            c = self.page.orig_qimg.pixelColor(x, y)
            self.colorPicked.emit((c.red(), c.green(), c.blue()))
        elif tool == 'roi':
            self._mode = 'roi'
            self._drag_start = ev.pos()
            self._roi_disp = QRect(ev.pos(), ev.pos())
            self.update()
        elif tool == 'pan':
            self._mode = 'pan'
            self._drag_start = ev.pos()
            self.setCursor(QCursor(Qt.ClosedHandCursor))

    def mouseMoveEvent(self, ev):
        if self._mode == 'divider' and (ev.buttons() & Qt.LeftButton):
            self.compare_x = max(0.0, min(1.0, ev.pos().x() / max(1, self.width())))
            self.update()
            return
        if self._mode == 'roi' and self._drag_start is not None:
            self._roi_disp = QRect(self._drag_start, ev.pos()).normalized()
            self.update()
            return
        if self._mode == 'pan' and (ev.buttons() & Qt.LeftButton):
            delta = ev.pos() - self._drag_start
            self._drag_start = ev.pos()
            sb = self.main.scroll
            sb.verticalScrollBar().setValue(
                sb.verticalScrollBar().value() - delta.y())
            sb.horizontalScrollBar().setValue(
                sb.horizontalScrollBar().value() - delta.x())
            return
        # 悬浮时给出光标提示
        if self.view_mode == 'compare':
            self.setCursor(QCursor(Qt.SplitHCursor))
        elif self.main.tool in ('pick', 'roi'):
            self.setCursor(QCursor(Qt.CrossCursor))
        else:
            self.setCursor(QCursor(Qt.OpenHandCursor))

    def mouseReleaseEvent(self, ev):
        if self._mode == 'roi' and self._drag_start is not None:
            r = self._roi_disp
            if r is not None and r.width() > 3 and r.height() > 3:
                x0, y0 = self.map_to_orig(r.topLeft())
                x1, y1 = self.map_to_orig(r.bottomRight())
                self.page.roi = (min(x0, x1), min(y0, y1),
                                 max(x0, x1), max(y0, y1))
                self.roiChanged.emit(self.page.roi)
            else:
                self.page.roi = None
                self._roi_disp = None
                self.roiChanged.emit(None)
            self.update()
        if self._mode == 'pan':
            self.setCursor(QCursor(Qt.OpenHandCursor))
        self._mode = None
        self._drag_start = None

    def refresh(self):
        """结果图变化后重绘（缓存的 QImage 已被 document 置空）。"""
        self.update()
