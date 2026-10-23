"""真实窗口的点击与截屏测试。"""
import ctypes
import sys
import time
from ctypes import wintypes

from PIL import ImageGrab

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

u = ctypes.WinDLL("user32")
u.FindWindowW.restype = wintypes.HWND
u.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]


def find():
    h = u.FindWindowW("NaiwaPetWindow", None)
    if not h:
        print("window not found")
        sys.exit(1)
    return h


def rect(h):
    r = wintypes.RECT()
    u.GetWindowRect(h, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def click(h):
    l, t, r, b = rect(h)
    # 点肚子中间偏下, 保证落在不透明像素上
    x = (l + r) // 2
    y = b - 70
    lp = ((y & 0xFFFF) << 16) | (x & 0xFFFF)
    u.PostMessageW(h, 0x0200, 0, lp)
    time.sleep(0.03)
    u.PostMessageW(h, 0x0201, 1, lp)
    time.sleep(0.06)
    u.PostMessageW(h, 0x0202, 0, lp)
    print("clicked at", x, y)


def shot(name):
    im = ImageGrab.grab()
    im.save(name)
    return im


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "click"
    h = find()
    l, t, r, b = rect(h)
    print("rect", l, t, r, b)
    if cmd == "click":
        click(h)
        time.sleep(0.45)
        im = shot(r"D:\Codex\奶蛙桌宠\.work\real_laugh.png")
        pad = 120
        box = (max(0, l - pad), max(0, t - pad), min(im.width, r + pad), min(im.height, b + pad))
        im.crop(box).save(r"D:\Codex\奶蛙桌宠\.work\real_crop.png")
        print("saved")
    elif cmd == "shot":
        im = shot(r"D:\Codex\奶蛙桌宠\.work\real_shot.png")
        print("saved", im.size)
