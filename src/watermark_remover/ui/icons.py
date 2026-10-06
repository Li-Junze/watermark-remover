"""程序化绘制的矢量风格图标（QPainter），避免引入图标资源文件。

所有图标按 24x24 网格设计，2x 超采样绘制保证高分屏清晰。
"""
from PyQt5.QtCore import Qt, QRectF, QLineF
from PyQt5.QtGui import (QBrush, QColor, QIcon, QLinearGradient, QPainter,
                         QPainterPath, QPen, QPixmap)

STROKE = '#4b5563'   # 工具栏图标描边色


def _icon(draw_fn, color=STROKE, size=20):
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.7)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.scale(size / 24.0, size / 24.0)
    draw_fn(p)
    p.end()
    return QIcon(pm)


def _poly(p, pts, close=False):
    path = QPainterPath()
    path.moveTo(*pts[0])
    for pt in pts[1:]:
        path.lineTo(*pt)
    if close:
        path.closeSubpath()
    p.drawPath(path)


def _line(p, *args):
    p.drawLine(QLineF(*args))


def _folder(p):
    _poly(p, [(3.5, 20), (3.5, 5.5), (9.5, 5.5), (11.5, 8.2), (20.5, 8.2),
              (20.5, 20)], close=True)
    _line(p, 3.5, 11.5, 20.5, 11.5)


def _zoom_in(p):
    p.drawEllipse(QRectF(4, 4, 12.5, 12.5))
    _line(p, 15.6, 15.6, 20.2, 20.2)
    _line(p, 10.2, 7.6, 10.2, 12.8)
    _line(p, 7.6, 10.2, 12.8, 10.2)


def _zoom_out(p):
    p.drawEllipse(QRectF(4, 4, 12.5, 12.5))
    _line(p, 15.6, 15.6, 20.2, 20.2)
    _line(p, 7.6, 10.2, 12.8, 10.2)


def _fit_width(p):
    _line(p, 4.5, 7, 4.5, 17)
    _line(p, 19.5, 7, 19.5, 17)
    _line(p, 8, 12, 16, 12)
    _poly(p, [(10.2, 9.6), (7.8, 12), (10.2, 14.4)])
    _poly(p, [(13.8, 9.6), (16.2, 12), (13.8, 14.4)])


def _actual_size(p):
    p.drawRoundedRect(QRectF(3.5, 5.5, 17, 13), 2.5, 2.5)
    f = p.font()
    f.setPixelSize(9)
    f.setBold(True)
    p.setFont(f)
    p.drawText(QRectF(3.5, 5.5, 17, 13), Qt.AlignCenter, '1:1')


def open_icon(color=STROKE):
    return _icon(_folder, color)


def zoom_in_icon(color=STROKE):
    return _icon(_zoom_in, color)


def zoom_out_icon(color=STROKE):
    return _icon(_zoom_out, color)


def fit_width_icon(color=STROKE):
    return _icon(_fit_width, color)


def actual_size_icon(color=STROKE):
    return _icon(_actual_size, color)


def make_app_icon():
    """应用图标：蓝色渐变圆角方块 + 白色橡皮擦。"""
    pm = QPixmap(256, 256)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    grad = QLinearGradient(0, 0, 256, 256)
    grad.setColorAt(0.0, QColor('#3b82f6'))
    grad.setColorAt(1.0, QColor('#1d4ed8'))
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(16, 16, 224, 224, 56, 56)

    # 橡擦主体（斜置）
    p.save()
    p.translate(118, 138)
    p.rotate(-45)
    p.setBrush(QBrush(QColor('#ffffff')))
    p.drawRoundedRect(-30, -78, 60, 128, 20, 20)
    p.setBrush(QBrush(QColor('#bfdbfe')))
    p.drawRoundedRect(-30, -6, 60, 12, 6, 6)
    p.restore()

    # 擦除碎屑
    p.setBrush(QBrush(QColor('#ffffff')))
    for cx, cy, r in ((178, 74, 9), (196, 100, 6), (162, 52, 5)):
        p.drawEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))
    p.end()
    return QIcon(pm)
