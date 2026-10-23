"""离线预览: 不建窗口, 直接把 render() 出来的帧合成到假桌面上, 检查观感。"""
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import win


class DummyWin:
    def __init__(self, *a, **k):
        self.hwnd = 1
        self.x = 0
        self.y = 0
        self.data = None

    def move(self, *a):
        pass

    def draw(self, data):
        self.data = data

    def show(self, *a):
        pass

    def set_topmost(self, *a):
        pass

    def resize(self, *a):
        pass


class DummyTray:
    ok = False

    def __init__(self, *a, **k):
        pass

    def remove(self):
        pass


win.LayeredWindow = DummyWin
win.Tray = DummyTray
win.load_config = lambda: {"size": os.environ.get("PET_SIZE", "mid")}
win.save_config = lambda c: None
win.autostart_enabled = lambda: True

import main  # noqa

pet = main.Pet()
pet.tray = DummyTray()


def frame_rgba():
    pet.render()
    w, h = pet.CW, pet.CH
    raw = np.frombuffer(pet.win.data, np.uint8).reshape(h, w, 4).astype(np.float32)
    b, g, r, a = raw[..., 0], raw[..., 1], raw[..., 2], raw[..., 3]
    # 反预乘
    k = np.maximum(a, 1e-3) / 255.0
    rgb = np.dstack([r / k, g / k, b / k]).clip(0, 255)
    return Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), "RGBA")


def desktop(w, h, dark=False):
    img = Image.new("RGB", (w, h), (28, 34, 46) if dark else (108, 132, 168))
    d = ImageDraw.Draw(img)
    for i in range(h):
        t = i / h
        c = (int(30 + 22 * t), int(38 + 26 * t), int(56 + 30 * t)) if dark else \
            (int(92 + 60 * t), int(120 + 60 * t), int(158 + 50 * t))
        d.line([(0, i), (w, i)], fill=c)
    d.rectangle((0, h - 42, w, h), fill=(22, 24, 30) if dark else (238, 238, 240))
    return img


def shot(name, dark=False, states=None):
    fr = frame_rgba()
    bg = desktop(fr.width + 160, fr.height + 90, dark)
    bg.paste(fr, (80, 40), fr)
    return bg


if __name__ == "__main__":
    out = []
    # 1. 待机 + 气泡
    pet.state = "idle"
    pet.sy, pet.sx, pet.angle = 1.0, 1.0, 0.0
    pet.say("今天也要加油", 3.0)
    pet.bubble_born -= 0.4
    out.append(("idle_bubble", shot("idle")))
    # 2. 眨眼
    pet.blink_until = time.perf_counter() + 1
    pet.eyes_closed = True
    pet.bubble_img = None
    out.append(("blink", shot("blink")))
    pet.eyes_closed = False
    # 3. 走路
    pet.state = "walk"
    pet.walk_dir = 1
    pet.walk_target = pet.feet_x + 40
    pet.state_t = 0.05
    pet.update(0.0, time.perf_counter())
    out.append(("walk", shot("walk")))
    # 4. 摸头(爱心)
    pet.state = "pat"
    pet.state_t = 0.25
    pet.eyes_closed = True
    pet.hearts = []
    pet.pat_hearts = None
    for i in range(3):
        pet.hearts.append({"x": pet.CW / 2 + (i - 1) * 26, "y": pet.CH - 12 - pet.pet_h * 0.9 - i * 18,
                           "vy": -30, "life": 2.0, "age": 0.4 * i, "drift": 3})
    out.append(("pat", shot("pat")))
    # 4.5 捧腹大笑
    pet.state = "pat"
    pet.hearts = []
    pet.flip = False
    pet.facing_right = False
    pet.laugh()
    pet.bubble_img = None
    pet.state_t = 0.55
    pet.eyes_closed = True
    pet.update(0.0, time.perf_counter())
    for i, hb in enumerate(pet.hahas):
        hb["age"] = 0.25 * i
        hb["y"] += hb["vy"] * hb["age"]
    out.append(("laugh", shot("laugh")))
    # 5. 吃东西
    pet.state = "eat"
    pet.flip = True
    pet.facing_right = True
    pet.state_t = 0.8
    pet.cookie = 0.8
    pet.eyes_closed = False
    pet.hearts = []
    out.append(("eat", shot("eat")))
    # 6. 睡觉
    pet.state = "sleep"
    pet.cookie = None
    pet.eyes_closed = True
    pet.say("Zzz…", 4.0)
    out.append(("sleep", shot("sleep", dark=True)))
    # 7. 悬浮/拖拽
    pet.state = "drag"
    pet.flip = False
    pet.facing_right = False
    pet.angle = 6
    pet.sy, pet.sx = 1.03, 0.97
    pet.bubble_img = None
    pet.eyes_closed = False
    pet.vx = 10
    out.append(("drag", shot("drag")))

    W = sum(o[1].width for o in out[:4]) + 30
    H = max(o[1].height for o in out[:4])
    sheet = Image.new("RGB", (W, H * 2 + 40), (250, 250, 250))
    x = 0
    for name, im in out[:4]:
        sheet.paste(im, (x, 0))
        x += im.width + 10
    x = 0
    for name, im in out[4:]:
        sheet.paste(im, (x, H + 30))
        x += im.width + 10
    sheet.save(os.path.join(ROOT, ".work", "sheet.png"))
    print("saved sheet", sheet.size)
