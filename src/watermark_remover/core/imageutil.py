"""QImage <-> numpy 互转工具。

所有去水印处理都在 numpy 的 RGB(uint8) 数组上进行，
显示用的 QImage 只在需要时由数组生成。
"""
import numpy as np
from PyQt5.QtGui import QImage


def qimage_to_rgb(img: QImage) -> np.ndarray:
    """任意格式 QImage -> HxWx3 uint8 (RGB, 通道顺序 R,G,B)。

    使用 Format_RGB888 读取，避免 RGB32(BGRA 内存序) 引起的通道错位。
    扫描行可能因 4 字节对齐而带填充，故按 bytesPerLine 取数再裁出有效宽度。
    """
    img = img.convertToFormat(QImage.Format_RGB888)
    w, h = img.width(), img.height()
    bpl = img.bytesPerLine()
    ptr = img.constBits()
    ptr.setsize(bpl * h)
    flat = np.frombuffer(ptr, dtype=np.uint8).reshape(h, bpl)
    return flat[:, : w * 3].reshape(h, w, 3).copy()


def rgb_to_qimage(arr: np.ndarray) -> QImage:
    """HxWx3 uint8 (RGB) -> QImage(Format_RGB888)，自持有数据（不引用外部 buffer）。"""
    arr = np.ascontiguousarray(arr, dtype=np.uint8)
    h, w = arr.shape[:2]
    img = QImage(arr.tobytes(), w, h, w * 3, QImage.Format_RGB888)
    return img.copy()
