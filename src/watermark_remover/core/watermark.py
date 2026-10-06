"""去水印核心算法（纯 numpy，可独立于界面测试）。

把「目标颜色范围内」的像素替换成「指定色」（默认白色）。
支持容差（颜色范围）与边缘柔化（软过渡），以及可选的矩形选区（ROI）。
"""
import numpy as np


def remove_watermark(rgb, target, tol, feather, fill, roi=None):
    """把 rgb 中接近 target 的像素替换为 fill。

    参数
    ----
    rgb     : HxWx3 uint8 原图
    target  : (r,g,b) 目标水印颜色
    tol     : 容差，0-255，三通道取最大差不超过 tol 即判定为同色
    feather : 边缘柔化，0 关闭；>0 时在 (tol-feather, tol] 区间做软过渡
    fill    : (r,g,b) 替换为的颜色，默认白色 (255,255,255)
    roi     : (x0,y0,x1,y1) 像素坐标，仅在该矩形内处理；None=整页

    返回
    ----
    (out, changed)  out: HxWx3 uint8；changed: 被替换的像素数
    """
    rgb = rgb.astype(np.float32)
    dr = np.abs(rgb[:, :, 0] - target[0])
    dg = np.abs(rgb[:, :, 1] - target[1])
    db = np.abs(rgb[:, :, 2] - target[2])
    d = np.maximum(dr, np.maximum(dg, db))

    mask = d <= tol
    if roi is not None:
        x0, y0, x1, y1 = [int(v) for v in roi]
        H, W = rgb.shape[:2]
        yy, xx = np.ogrid[:H, :W]
        roi_mask = (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)
        mask = mask & roi_mask

    out = rgb.copy()
    # rem = 用 fill 替换的比例；默认整块替换为 1.0
    rem = np.ones_like(d, dtype=np.float32)
    if feather > 0:
        band = (d > tol - feather) & (d <= tol)
        rem[band] = 1.0 - (d[band] - (tol - feather)) / feather
    rem = rem * mask  # 只在命中且容差内的像素生效

    for c in range(3):
        out[:, :, c] = rgb[:, :, c] * (1.0 - rem) + fill[c] * rem

    return out.astype(np.uint8), int(mask.sum())
