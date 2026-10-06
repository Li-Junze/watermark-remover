"""去水印核心算法的单元测试（仅依赖 numpy，无 Qt）。

运行：python tests/test_watermark.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'src'))

import numpy as np

from watermark_remover.core.watermark import remove_watermark


def make_img():
    """10x10 白底，中央 4x4 灰色（200）水印块。"""
    img = np.full((10, 10, 3), 255, dtype=np.uint8)
    img[3:7, 3:7] = 200
    return img


def test_exact_replacement():
    img = make_img()
    out, changed = remove_watermark(img, (200, 200, 200), tol=0, feather=0,
                                    fill=(255, 255, 255))
    assert changed == 16, changed
    assert (out[3:7, 3:7] == 255).all()
    # 水印外像素不受影响
    assert (out[0, 0] == 255).all()


def test_tolerance():
    img = make_img()
    # 容差 30 应包含 200±30 内的颜色
    img2 = img.copy()
    img2[0, 0] = 180
    out, changed = remove_watermark(img2, (200, 200, 200), tol=30, feather=0,
                                    fill=(255, 255, 255))
    assert changed == 17, changed
    assert (out[0, 0] == 255).all()
    # 容差 10 时 180 不应被替换
    out2, changed2 = remove_watermark(img2, (200, 200, 200), tol=10, feather=0,
                                      fill=(255, 255, 255))
    assert changed2 == 16, changed2
    assert (out2[0, 0] == 180).all()


def test_fill_color():
    img = make_img()
    out, changed = remove_watermark(img, (200, 200, 200), tol=0, feather=0,
                                    fill=(0, 128, 255))
    assert (out[3, 3] == (0, 128, 255)).all()


def test_feather_soft_edge():
    img = make_img()
    # 造一行渐变：距离 0,2,4,6,8
    row = np.array([200, 198, 196, 194, 192, 190, 188, 186, 184, 182],
                   dtype=np.uint8)
    img = np.stack([row] * 10, axis=0)
    img = np.stack([img] * 3, axis=-1)
    out, _ = remove_watermark(img, (200, 200, 200), tol=10, feather=10,
                              fill=(255, 255, 255))
    # 距离 0 -> 完全替换为白
    assert out[0, 0, 0] == 255
    # 距离 10（=tol）-> 不替换
    assert out[0, 10 - 1, 0] == 182
    # 中间应有介于 182 与 255 之间的过渡值
    mid = out[0, 5, 0]
    assert 182 < mid < 255, mid


def test_roi():
    img = make_img()
    out, changed = remove_watermark(img, (200, 200, 200), tol=0, feather=0,
                                    fill=(255, 255, 255), roi=(0, 0, 4, 4))
    # ROI (0,0)-(4,4) 与水印块 [3:7,3:7] 的交集是 rows 3-4 x cols 3-4 = 4 像素
    assert changed == 4, changed
    assert (out[3:5, 3:5] == 255).all()
    # ROI 外的水印像素保留
    assert (out[5, 5] == 200).all()


if __name__ == '__main__':
    fns = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    for fn in fns:
        fn()
        print(f'PASS  {fn.__name__}')
    print(f'\nAll {len(fns)} tests passed.')
