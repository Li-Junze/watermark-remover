"""支持 `python -m watermark_remover` 启动。"""
import sys

from .app import main

if __name__ == "__main__":
    main(sys.argv)
