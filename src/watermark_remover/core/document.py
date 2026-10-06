"""文档加载 / 多页管理 / 处理 / 导出。

- PDF 用 PyMuPDF(fitz) 渲染为 RGB 数组；
- 图片直接用 Pillow 读成 RGB 数组；
- 每页保存原图(orig)与结果(res)两份数组，处理只改 res；
- 导出 PDF 时把每页结果数组写回，全程本地、零网络。
"""
import io

import fitz
import numpy as np
from PIL import Image

from .imageutil import rgb_to_qimage
from .watermark import remove_watermark

# 渲染倍率：相对 PDF 页面默认尺寸放大，兼顾清晰度与内存
RENDER_SCALE = 2.0


class Page:
    """单页：持有原图与结果图（均为 HxWx3 uint8）。"""

    def __init__(self, orig_arr: np.ndarray):
        self.orig_arr = np.ascontiguousarray(orig_arr, dtype=np.uint8)
        self.res_arr = self.orig_arr.copy()
        self.roi = None            # (x0,y0,x1,y1) 像素坐标，None=整页
        self._orig_qimg = None
        self._res_qimg = None

    @property
    def orig_qimg(self):
        if self._orig_qimg is None:
            self._orig_qimg = rgb_to_qimage(self.orig_arr)
        return self._orig_qimg

    @property
    def res_qimg(self):
        if self._res_qimg is None:
            self._res_qimg = rgb_to_qimage(self.res_arr)
        return self._res_qimg

    def process(self, target, tol, feather, fill, use_roi=True):
        roi = self.roi if use_roi else None
        self.res_arr, changed = remove_watermark(
            self.orig_arr, target, tol, feather, fill, roi)
        self._res_qimg = None
        return changed

    def restore(self):
        self.res_arr = self.orig_arr.copy()
        self._res_qimg = None


class Doc:
    """文档：PDF 或单张图片，包含若干 Page。"""

    def __init__(self):
        self.pages = []
        self.path = None
        self.kind = None          # 'pdf' | 'image'
        self.pdf_doc = None
        self.filename = None

    # ---- 加载 ----
    def load_pdf(self, path):
        self.close()
        self.pdf_doc = fitz.open(path)
        self.pages = []
        for i in range(self.pdf_doc.page_count):
            pg = self.pdf_doc[i]
            mat = fitz.Matrix(RENDER_SCALE, RENDER_SCALE)
            pix = pg.get_pixmap(matrix=mat)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n)
            if pix.n == 4:
                arr = arr[:, :, :3]
            elif pix.n == 1:
                arr = np.repeat(arr[:, :, 0:1], 3, axis=2)
            else:
                arr = arr[:, :, :3]
            self.pages.append(Page(arr))
        self.path = path
        self.filename = path
        self.kind = 'pdf'

    def load_image(self, path):
        self.close()
        img = Image.open(path).convert('RGB')
        arr = np.asarray(img)
        self.pages = [Page(arr)]
        self.path = path
        self.filename = path
        self.kind = 'image'

    def close(self):
        if self.pdf_doc is not None:
            try:
                self.pdf_doc.close()
            except Exception:
                pass
        self.pdf_doc = None

    # ---- 处理 ----
    def process_page(self, idx, target, tol, feather, fill, use_roi=True):
        return self.pages[idx].process(target, tol, feather, fill, use_roi)

    def process_all(self, target, tol, feather, fill, use_roi=True):
        total = 0
        for pg in self.pages:
            total += pg.process(target, tol, feather, fill, use_roi)
        return total

    def restore_page(self, idx):
        self.pages[idx].restore()

    def restore_all(self):
        for pg in self.pages:
            pg.restore()

    # ---- 导出 ----
    def export_pdf(self, out_path, target, tol, feather, fill, process_all=True):
        """把所有页按相同规则合成导出为 PDF。"""
        new = fitz.open()
        for pg in self.pages:
            if process_all:
                arr = remove_watermark(
                    pg.orig_arr, target, tol, feather, fill,
                    pg.roi if pg.roi is not None else None)[0]
            else:
                arr = pg.res_arr
            h, w = arr.shape[:2]
            # 用 Pillow 写成 PNG 字节流，再交给 fitz 写入（避开 Pixmap 原料构造差异）
            im = Image.fromarray(arr.astype(np.uint8))
            buf = io.BytesIO()
            im.save(buf, format='PNG')
            page = new.new_page(width=w, height=h)
            page.insert_image(page.rect, stream=buf.getvalue())
        new.save(out_path)
        new.close()
