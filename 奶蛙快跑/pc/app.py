# -*- coding: utf-8 -*-
"""奶蛙快跑 - PC 端启动器

开发模式：直接 python app.py （需要 pip install pywebview）
打包后：  奶蛙快跑.exe 双击即玩（窗口内渲染游戏页面，键盘空格跳跃）
"""
import os
import sys


def ui_path():
    if getattr(sys, "frozen", False):          # PyInstaller 打包后
        base = sys._MEIPASS
    else:                                       # 源码运行：项目根目录
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "index.html")


def main():
    import webview

    webview.create_window(
        "奶蛙快跑",
        ui_path(),
        width=540,
        height=960,
        min_size=(360, 640),
        resizable=True,
        background_color="#F7EBD5",
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
