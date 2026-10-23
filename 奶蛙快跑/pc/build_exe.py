# -*- coding: utf-8 -*-
"""把游戏打包成单个 PC exe（输出 奶蛙快跑/dist/奶蛙快跑.exe）"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
PY = sys.executable

cmd = [
    PY, "-m", "PyInstaller",
    "--noconfirm", "--clean", "--onefile", "--windowed",
    "--name", "奶蛙快跑",
    "--add-data", os.path.join(GAME, "index.html") + ";.",
    "--add-data", os.path.join(GAME, "assets") + ";assets",
    "--add-data", os.path.join(GAME, "vendor") + ";vendor",
    "--icon", os.path.join(GAME, "..", "assets", "tray.ico"),
    "--distpath", os.path.join(GAME, "dist"),
    "--workpath", os.path.join(GAME, "build"),
    "--specpath", os.path.join(GAME, "build"),
    os.path.join(HERE, "app.py"),
]
print(" ".join(cmd))
raise SystemExit(subprocess.call(cmd))
