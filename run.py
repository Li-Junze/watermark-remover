#!/usr/bin/env python3
"""便捷启动器：无需安装，直接 `python run.py [文件]` 运行。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))

from watermark_remover.app import main

if __name__ == "__main__":
    main(sys.argv)
