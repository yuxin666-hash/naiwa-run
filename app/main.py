"""奶蛙快跑 - 主程序"""
import ctypes
import math
import os
import random
import sys
import time

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art
import win

SIZES = {"small": 120, "mid": 180, "big": 260}
SIZE_LABEL = {"small": "小号", "mid": "中号", "big": "大号"}

M_PAT, M_FEED, M_WALK, M_SLEEP, M_LAUGH = 1001, 1002, 1003, 1004, 1005
M_SMALL, M_MID, M_BIG = 1101, 1102, 1103
M_TOPMOST, M_AUTOSTART = 1200, 1201
M_HIDE, M_QUIT = 1900, 1901
SIZE_ID = {"small": M_SMALL, "mid": M_MID, "big": M_BIG}
SIZE_BY_ID = {v: k for k, v in SIZE_ID.items()}

LINES_TAP = ["咕噜~", "好舒服呀", "再摸一下嘛", "嘿嘿…", "痒痒的"]
LINES_LAUGH = ["哈哈哈哈哈！", "笑死我了", "哈哈哈哈！", "咯咯咯…哈哈！", "嘿嘿嘿嘿~"]
LINES_FEED = ["谢谢！", "好吃…", "还在长身体呢", "嗝~", "再来一口？"]
LINES_IDLE = ["今天也要加油", "要不要休息一下？", "我在看着你哦", "肚子有点饿了…",
              "摸鱼中…", "你忙你的，我陪着你"]
LINES_SLEEP = ["困了…", "Zzz…"]
LINES_WAKE = ["唔…醒了", "再睡五分钟…", "嗯？"]


class Pet:
    def __init__(self):
        self.cfg = win.load_config()
        self.size_key = self.cfg.get("size", "mid")
        if self.size_key not in SIZES:
            self.size_key = "mid"
        self.topmost = bool(self.cfg.get("topmost", True))
        self.running = True
        self.pending_menu = None
        self.visible = True
        self.last_canvas = None

        self.wa = win.work_area()
        self.ground = self.wa[3] - 10
        self.feet_x = float(self.cfg.get("x", self.wa[2] - 150))
        self.feet_y = float(self.ground)

        # 动画状态
        self.state = "idle"
        self.t = 0.0
        self.state_t = 0.0
        self.sx, self.sy = 1.0, 1.0
        self.angle = 0.0
        self.flip = False
        self.dy = 0.0
        self.eyes_closed = False
        self.blink_until = 0.0
        self.next_blink = time.perf_counter() + random.uniform(2.0, 5.0)
        self.next_action = time.perf_counter() + random.uniform(5.0, 9.0)
        self.last_interaction = time.perf_counter()
        self.last_touch = 0.0

        self.bubble_img = None
        self.bubble_born = 0.0
        self.bubble_life = 0.0
        self.hearts = []
        self.hahas = []
        self.cookie = None
        self.walk_target = None
        self.walk_dir = 1
        self.vy = 0.0
        self.drag = None
        self.vx = 0.0
        self.last_render = 0.0

        self.build_sprite()
        wx = int(self.feet_x - self.CW / 2)
        wy = int(self.feet_y - (self.CH - self.bottom_pad))
        self.win = win.LayeredWindow(self.CW, self.CH, wx, wy, self.on_message)
        if self.topmost:
            self.win.set_topmost(True)
        self.tray = win.Tray(self.win.hwnd, os.path.join(art.ASSETS, "tray.ico"))
        if not self.tray.ok:
            print("托盘图标创建失败, 隐藏功能会不可用", flush=True)
        self.win.show(True)
        self.first_run = "size" not in self.cfg
        self.render()

    # ---------------- 尺寸 / 素材 ----------------
    def build_sprite(self):
        self.dpi = getattr(self, "dpi", None) or win.dpi_scale()
        self.pet_h = int(round(SIZES[self.size_key] * self.dpi))
        self.sprite = art.Sprite(self.pet_h)
        self.bottom_pad = 12
        self.jump_room = int(self.pet_h * 0.28) + 10
        self.bubble_room = 120
        self.CW = max(290, int(self.sprite.w + 190))
        self.CH = self.bottom_pad + self.pet_h + self.jump_room + self.bubble_room
        self.shadow_cache = {}
        self._heart_cache = {}
        self._ha_cache = {}
        self.heart_img = art.heart(max(12, int(self.pet_h * 0.095)))
        self.cookie_img = art.cookie(max(14, int(self.pet_h * 0.10)))

    def heart_faded(self, level):
        img = self._heart_cache.get(level)
        if img is None:
            img = self.heart_img.copy()
            img.putalpha(img.getchannel("A").point([int(i * level) for i in range(256)]))
            self._heart_cache[level] = img
        return img

    def ha_faded(self, size, level):
        key = (size, level)
        img = self._ha_cache.get(key)
        if img is None:
            img = art.ha_glyph(size)
            img = img.copy()
            img.putalpha(img.getchannel("A").point([int(i * level) for i in range(256)]))
            if len(self._ha_cache) > 40:
                self._ha_cache.clear()
            self._ha_cache[key] = img
        return img

    def shadow_for(self, k):
        key = round(max(0.2, min(1.15, k)), 2)
        img = self.shadow_cache.get(key)
        if img is None:
            img = self.sprite.shadow(key)
            self.shadow_cache[key] = img
        return img

    def apply_size(self, key):
        fx, fy = self.feet_x, self.feet_y
        self.size_key = key
        self.build_sprite()
        self.win.resize(self.CW, self.CH)
        self.feet_x, self.feet_y = fx, min(fy, self.ground)
        self.sync_window()
        self.cfg["size"] = key
        win.save_config(self.cfg)
        self.render()

    def sync_window(self):
        self.win.move(self.feet_x - self.CW / 2, self.feet_y - (self.CH - self.bottom_pad))

    # ---------------- 消息 ----------------
    def on_message(self, hwnd, msg, wparam, lparam):
        if msg == win.WM_NCHITTEST:
            x = ctypes.c_short(lparam & 0xFFFF).value
            y = ctypes.c_short((lparam >> 16) & 0xFFFF).value
            cx, cy = x - self.win.x, y - self.win.y
            a = self.alpha_at(cx, cy)
            return win.HTCLIENT if a > 16 else win.HTTRANSPARENT
        if msg == win.WM_MOUSEACTIVATE:
            return win.MA_NOACTIVATE
        if msg == win.WM_LBUTTONDOWN:
            self.on_down()
            return 0
        if msg == win.WM_MOUSEMOVE:
            self.on_move()
            return 0
        if msg == win.WM_LBUTTONUP:
            self.on_up()
            return 0
        if msg == win.WM_LBUTTONDBLCLK:
            self.drag = None
            self.feed()
            return 0
        if msg == win.WM_RBUTTONUP:
            self.pending_menu = "pet"
            return 0
        if msg == win.WM_APP_TRAY:
            if lparam in (win.WM_RBUTTONUP,):
                self.pending_menu = "tray"
            elif lparam == win.WM_LBUTTONDBLCLK:
                self.toggle_visible()
            return 0
        if msg == win.WM_CLOSE:
            self.quit()
            return 0
        if msg == win.WM_DESTROY:
            self.running = False
            return 0
        return win.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def alpha_at(self, cx, cy):
        cv = self.last_canvas
        if cv is None:
            return 255
        w, h = cv.size
        if 0 <= cx < w and 0 <= cy < h:
            return cv.getpixel((int(cx), int(cy)))[3]
        return 0

    def on_down(self):
        pt = win.POINT()
        win.user32.GetCursorPos(ctypes.byref(pt))
        self.drag = {"sx": pt.x - self.win.x, "sy": pt.y - self.win.y,
                     "ox": self.win.x, "oy": self.win.y, "moved": 0.0, "lx": pt.x}
        win.user32.SetCapture(self.win.hwnd)
        self.last_interaction = time.perf_counter()
        if self.state == "sleep":
            self.wake()
        else:
            self.state = "drag"
            self.state_t = 0.0
        self.cookie = None

    def on_move(self):
        if not self.drag:
            return
        pt = win.POINT()
        win.user32.GetCursorPos(ctypes.byref(pt))
        nx = pt.x - self.drag["sx"]
        ny = pt.y - self.drag["sy"]
        self.drag["moved"] += abs(nx - self.win.x) + abs(ny - self.win.y)
        self.vx = (pt.x - self.drag["lx"]) * 0.6 + self.vx * 0.4
        self.drag["lx"] = pt.x
        self.win.move(nx, ny)
        self.feet_x = self.win.x + self.CW / 2
        self.feet_y = self.win.y + (self.CH - self.bottom_pad)

    def on_up(self):
        win.user32.ReleaseCapture()
        if not self.drag:
            return
        moved = self.drag["moved"]
        self.drag = None
        if moved < 7:
            self.laugh()
        else:
            # 松手: 落到桌面底部
            self.state = "fall"
            self.state_t = 0.0
            self.vy = 0.0

    def toggle_visible(self):
        self.visible = not self.visible
        self.win.show(self.visible)

    def quit(self):
        self.cfg["x"] = int(self.feet_x)
        win.save_config(self.cfg)
        try:
            self.tray.remove()
        except Exception:
            pass
        self.running = False
        win.user32.PostQuitMessage(0)

    # ---------------- 动作 ----------------
    def say(self, text, life=2.2, font_px=None):
        fp = font_px or max(12, int(self.pet_h * 0.078))
        self.bubble_img = art.Bubble.make(text, font_px=fp,
                                          max_w=int(self.CW * 0.78))
        self.bubble_born = time.perf_counter()
        self.bubble_life = life

    def pat(self):
        self.last_interaction = time.perf_counter()
        self.state = "pat"
        self.state_t = 0.0
        if self.state != "sleep":
            self.say(random.choice(LINES_TAP), 1.8)
        for _ in range(random.randint(2, 4)):
            self.hearts.append({
                "x": self.CW / 2 + random.uniform(-self.pet_h * 0.30, self.pet_h * 0.30),
                "y": self.CH - self.bottom_pad - self.pet_h * 1.02 - random.uniform(0, 8),
                "vy": -random.uniform(34, 52),
                "life": 1.4, "age": 0.0,
                "drift": random.uniform(-14, 14)})

    def laugh(self):
        self.last_interaction = time.perf_counter()
        self.state = "laugh"
        self.state_t = 0.0
        self.say(random.choice(LINES_LAUGH), 2.0)
        # 身体两侧各飘几只「哈」, 不压住脸和气泡
        base = max(15, int(self.pet_h * 0.125))
        n = random.randint(3, 5)
        for i in range(n):
            side = 1.0 if i % 2 else -1.0
            self.hahas.append({
                "x": self.CW / 2 + side * self.pet_h * random.uniform(0.34, 0.56),
                "y": self.CH - self.bottom_pad - self.pet_h * random.uniform(0.70, 1.10),
                "vy": -random.uniform(30, 46),
                "life": 1.9, "age": random.uniform(0.0, 0.55),
                "drift": side * random.uniform(6, 16),
                "size": int(base * random.uniform(0.70, 1.15)),
                "wob": random.uniform(0.0, math.tau)})

    def feed(self):
        self.last_interaction = time.perf_counter()
        if self.state == "sleep":
            self.wake()
        self.state = "eat"
        self.state_t = 0.0
        self.cookie = 0.0

    def sleep(self):
        self.state = "sleep"
        self.state_t = 0.0
        self.say(random.choice(LINES_SLEEP), 2.0)

    def wake(self):
        self.state = "idle"
        self.state_t = 0.0
        self.last_interaction = time.perf_counter()
        self.say(random.choice(LINES_WAKE), 1.6)

    def start_walk(self):
        left, _, right, _ = self.wa
        for _ in range(8):
            tx = random.uniform(left + 90, right - 90)
            if abs(tx - self.feet_x) > self.pet_h * 0.8:
                break
        self.walk_target = tx
        self.walk_dir = 1 if tx > self.feet_x else -1
        self.state = "walk"
        self.state_t = 0.0

    # ---------------- 更新 ----------------
    def update(self, dt, now):
        self.t += dt
        self.state_t += dt
        st = self.state
        if st != "sleep" and now - self.last_interaction > 150:
            self.sleep()

        if st == "idle":
            b = math.sin(self.t * 2 * math.pi * 0.26)
            self.sy = 1 + 0.017 * b
            self.sx = 1 - 0.011 * b
            self.angle = 1.0 * math.sin(self.t * 0.55)
            self.dy = 0.0
            if now > self.next_action and not self.bubble_img:
                self.next_action = now + random.uniform(7, 18)
                r = random.random()
                if r < 0.44:
                    self.start_walk()
                elif r < 0.58:
                    self.state = "jump"
                    self.state_t = 0.0
                elif r < 0.74:
                    self.say(random.choice(LINES_IDLE), 2.6)
                elif r < 0.84:
                    self.state = "look"
                    self.state_t = 0.0

        elif st == "look":
            p = self.state_t / 1.6
            self.sy = 1 + 0.012 * math.sin(p * math.pi * 2)
            self.sx = 1 - 0.008 * math.sin(p * math.pi * 2)
            self.angle = 3.2 * math.sin(p * math.pi * 2)
            if p >= 1:
                self.state = "idle"
                self.angle = 0

        elif st == "walk":
            speed = self.pet_h * 0.42
            step = speed * dt
            remain = self.walk_target - self.feet_x
            if abs(remain) <= step:
                self.feet_x = self.walk_target
                self.state = "idle"
                self.state_t = 0.0
                self.sy, self.sx, self.angle = 1.0, 1.0, 0.0
                self.next_action = now + random.uniform(4, 9)
            else:
                self.feet_x += step * (1 if remain > 0 else -1)
                self.sync_window()
            ph = self.state_t * 9.0
            self.sy = 1 + 0.022 * abs(math.sin(ph))
            self.sx = 1 - 0.018 * abs(math.sin(ph))
            self.dy = -abs(math.sin(ph)) * self.pet_h * 0.025
            self.angle = 1.8 * self.walk_dir
            self.flip = self.walk_dir > 0

        elif st == "jump":
            T = 0.66
            p = min(1.0, self.state_t / T)
            h = self.pet_h * 0.26
            self.dy = -h * math.sin(math.pi * p)
            if p < 0.16:
                k = p / 0.16
                self.sy = 1 - 0.09 * math.sin(k * math.pi)
                self.sx = 1 + 0.06 * math.sin(k * math.pi)
            elif p > 0.9:
                k = (p - 0.9) / 0.1
                self.sy = 1 - 0.07 * math.sin(k * math.pi)
                self.sx = 1 + 0.05 * math.sin(k * math.pi)
            else:
                self.sy, self.sx = 1.02, 0.99
            self.angle = 1.5 * math.sin(p * math.pi)
            if p >= 1:
                self.state = "idle"
                self.state_t = 0.0
                self.dy = 0.0

        elif st == "pat":
            p = self.state_t / 1.15
            damp = max(0.0, 1 - p)
            self.sy = 1 + 0.07 * math.sin(p * math.pi * 4.5) * damp
            self.sx = 1 - 0.05 * math.sin(p * math.pi * 4.5) * damp
            self.angle = 2.2 * math.sin(p * math.pi * 3) * damp
            self.eyes_closed = p < 0.72
            if p >= 1:
                self.state = "idle"
                self.eyes_closed = False
                self.sy = self.sx = 1.0

        elif st == "laugh":
            # 捧腹大笑: 前仰后合 + 一颠一颠, 眯成缝
            p = self.state_t / 2.3
            damp = max(0.0, 1 - 0.55 * p)
            self.angle = 5.0 * math.sin(self.state_t * 11.0) * damp
            self.sy = 1 + 0.045 * math.sin(self.state_t * 13.5) * damp
            self.sx = 1 - 0.035 * math.sin(self.state_t * 13.5) * damp
            self.dy = -abs(math.sin(self.state_t * 6.7)) * self.pet_h * 0.030 * damp
            self.eyes_closed = True
            if p >= 1:
                self.state = "idle"
                self.eyes_closed = False
                self.sy = self.sx = 1.0
                self.dy = 0.0
                self.angle = 0.0

        elif st == "eat":
            self.eyes_closed = False
            if self.cookie is not None:
                self.cookie += dt
            p = self.state_t
            if p < 1.5:
                k = min(1.0, p / 0.55)
                self.angle = -2.0 * (1 - k)
                self.sy = 1 - 0.02 * math.sin(p * 4)
            elif p < 2.6:
                self.sy = 1 + 0.028 * math.sin((p - 1.5) * 17)
                self.sx = 1 - 0.02 * math.sin((p - 1.5) * 17)
                self.eyes_closed = True
            if p >= 2.8:
                self.state = "idle"
                self.cookie = None
                self.eyes_closed = False
                self.say(random.choice(LINES_FEED), 2.0)

        elif st == "drag":
            self.angle = max(-9, min(9, self.vx * 0.45))
            self.vx *= 0.86
            self.sy = 1.03
            self.sx = 0.97
            self.dy = 0.0
            self.eyes_closed = False

        elif st == "fall":
            self.vy += 2600 * dt
            self.feet_y += self.vy * dt
            if self.feet_y >= self.ground:
                self.feet_y = self.ground
                self.state = "land"
                self.state_t = 0.0
                self.vy = 0.0
            self.angle *= 0.9
            self.sy = 1.0
            self.sx = 1.0
            self.sync_window()

        elif st == "land":
            p = self.state_t / 0.34
            self.sy = 1 - 0.16 * math.sin(min(1.0, p) * math.pi) * (1 - p * 0.5)
            self.sx = 1 + 0.12 * math.sin(min(1.0, p) * math.pi) * (1 - p * 0.5)
            if p >= 1:
                self.state = "idle"
                self.sy = self.sx = 1.0
                self.next_action = now + random.uniform(3, 7)

        elif st == "sleep":
            b = math.sin(self.t * 2 * math.pi * 0.13)
            self.sy = 1 + 0.022 * b
            self.sx = 1 - 0.014 * b
            self.angle = 0.8 * math.sin(self.t * 0.3)
            self.eyes_closed = True
            if now > self.next_action:
                self.next_action = now + random.uniform(9, 16)
                if not self.bubble_img:
                    self.say("Zzz…", 3.0)

        # 眨眼
        if self.state in ("idle", "walk", "look"):
            if now > self.next_blink:
                self.blink_until = now + 0.13
                self.next_blink = now + random.uniform(2.6, 7.5)
            self.eyes_closed = now < self.blink_until

        # 爱心
        for hb in self.hearts:
            hb["age"] += dt
            hb["y"] += hb["vy"] * dt
            hb["x"] += hb["drift"] * dt
            hb["vy"] *= 0.985
        self.hearts = [h for h in self.hearts if h["age"] < h["life"]]

        # 「哈」
        for hb in self.hahas:
            hb["age"] += dt
            hb["y"] += hb["vy"] * dt
            hb["x"] += hb["drift"] * dt
            hb["vy"] *= 0.98
        self.hahas = [h for h in self.hahas if h["age"] < h["life"]]

        # 气泡计时
        if self.bubble_img is not None:
            if now - self.bubble_born > self.bubble_life + 0.35:
                self.bubble_img = None

    # ---------------- 绘制 ----------------
    def render(self):
        if not self.visible:
            return
        cv = Image.new("RGBA", (self.CW, self.CH), (0, 0, 0, 0))
        fx = self.CW / 2.0
        fy = self.CH - self.bottom_pad + self.dy

        # 影子
        k = 1.0 + self.dy / max(1.0, self.pet_h * 0.9)
        if self.state != "land":
            sh = self.shadow_for(k)
            if sh is not None:
                sw = sh.width
                cv.paste(sh, (int(fx - sw / 2), int(self.CH - self.bottom_pad - sh.height * 0.55)), sh)

        if self.state == "laugh":
            img = self.sprite.laugh
        elif self.eyes_closed:
            img = self.sprite.closed
        else:
            img = self.sprite.open
        out, pos = art.transform_sprite(img, self.sprite.anchor, (fx, fy),
                                       self.angle, self.sx, self.sy, self.flip)
        cv.paste(out, pos, out)

        # 饼干
        if self.state == "eat" and self.cookie is not None:
            p = self.cookie
            visible_from, arrive = 0.0, 0.75
            t = min(1.0, max(0.0, (p - visible_from) / arrive))
            ease = 1 - (1 - t) ** 3
            mx, my = self.sprite.mouth
            mox = mx - self.sprite.anchor[0]
            if self.flip:
                mox = -mox
            side = 1.0 if self.flip else -1.0
            start_x = fx + side * self.pet_h * 0.62
            start_y = fy - self.pet_h * 0.34
            end_x = fx + mox + side * self.pet_h * 0.05
            end_y = fy + (my - self.sprite.anchor[1]) + self.pet_h * 0.03
            cx = start_x + (end_x - start_x) * ease
            cy = start_y + (end_y - start_y) * ease
            if p < 1.75:
                ci = self.cookie_img
                cv.paste(ci, (int(cx - ci.width / 2), int(cy - ci.height / 2)), ci)

        # 气泡
        if self.bubble_img is not None:
            now = time.perf_counter()
            age = now - self.bubble_born
            f = 1.0
            if age < 0.16:
                f = age / 0.16
            elif age > self.bubble_life:
                f = max(0.0, 1 - (age - self.bubble_life) / 0.35)
            bi = self.bubble_img
            if f < 0.99:
                lut = [int(i * f) for i in range(256)]
                bi = bi.copy()
                bi.putalpha(bi.getchannel("A").point(lut))
            head_top = self.CH - self.bottom_pad - self.pet_h + 6 + self.dy
            bx = int(fx - bi.width / 2)
            by = int(head_top - bi.height + 4)
            if by < 2:
                by = 2
            cv.paste(bi, (bx, by), bi)

        # 爱心(画在气泡之上, 让粉心浮在最前)
        for hb in self.hearts:
            f = 1 - (hb["age"] / hb["life"])
            lv = round(min(1.0, f * 1.6) * 12) / 12.0
            if lv > 0.02:
                tmp = self.heart_faded(lv)
                cv.paste(tmp, (int(hb["x"]), int(hb["y"])), tmp)

        # 「哈哈」飘字
        for hb in self.hahas:
            f = 1 - (hb["age"] / hb["life"])
            lv = round(min(1.0, f * 1.9) * 10) / 10.0
            if lv > 0.02:
                tmp = self.ha_faded(hb["size"], lv)
                wob = math.sin(hb["age"] * 7 + hb["wob"]) * 3
                cv.paste(tmp, (int(hb["x"] + wob), int(hb["y"])), tmp)

        self.last_canvas = cv
        self.win.draw(cv.convert("RGBa").tobytes("raw", "BGRa"))

    # ---------------- 菜单 ----------------
    def pet_menu(self):
        sleeping = self.state == "sleep"
        sleep_label = "叫醒它" if sleeping else "睡一会儿"
        items = [
            (M_LAUGH, "捧腹大笑"),
            (M_PAT, "摸摸头"),
            (M_FEED, "喂一口"),
            (M_WALK, "散散步", False, self.state in ("drag", "fall", "sleep")),
            (M_SLEEP, sleep_label, False, self.state in ("drag", "fall")),
            ("-", None),
            ("sub", ("大小", [(M_SMALL, SIZE_LABEL["small"]),
                              (M_MID, SIZE_LABEL["mid"]),
                              (M_BIG, SIZE_LABEL["big"])],
                     {SIZE_ID[self.size_key]})),
            (M_TOPMOST, "总在最前", self.topmost),
            (M_AUTOSTART, "开机自启", win.autostart_enabled()),
            ("-", None),
            (M_HIDE, "藏起来（托盘图标唤回）", False, not self.tray.ok),
            (M_QUIT, "退出"),
        ]
        cmd = win.popup_menu(self.win.hwnd, items)
        return cmd

    def tray_menu(self):
        items = [
            (M_HIDE, "隐藏奶蛙" if self.visible else "显示奶蛙"),
            (M_LAUGH, "捧腹大笑"),
            (M_PAT, "摸摸头"),
            (M_FEED, "喂一口"),
            ("-", None),
            ("sub", ("大小", [(M_SMALL, SIZE_LABEL["small"]),
                              (M_MID, SIZE_LABEL["mid"]),
                              (M_BIG, SIZE_LABEL["big"])],
                     {SIZE_ID[self.size_key]})),
            (M_AUTOSTART, "开机自启", win.autostart_enabled()),
            ("-", None),
            (M_QUIT, "退出"),
        ]
        return win.popup_menu(self.win.hwnd, items)

    def handle_menu(self, which):
        cmd = self.pet_menu() if which == "pet" else self.tray_menu()
        self.last_interaction = time.perf_counter()
        if cmd == 0:
            return
        if cmd == M_LAUGH:
            self.laugh()
        elif cmd == M_PAT:
            self.pat()
        elif cmd == M_FEED:
            self.feed()
        elif cmd == M_WALK:
            self.wake() if self.state == "sleep" else None
            self.start_walk()
        elif cmd == M_SLEEP:
            self.wake() if self.state == "sleep" else self.sleep()
        elif cmd in (M_SMALL, M_MID, M_BIG):
            self.apply_size({M_SMALL: "small", M_MID: "mid", M_BIG: "big"}[cmd])
        elif cmd == M_TOPMOST:
            self.topmost = not self.topmost
            self.win.set_topmost(self.topmost)
            self.cfg["topmost"] = self.topmost
            win.save_config(self.cfg)
        elif cmd == M_AUTOSTART:
            on = not win.autostart_enabled()
            win.set_autostart(on)
            self.say("开机就会见到我啦" if on else "那我就不自动出现啦", 2.2)
        elif cmd == M_HIDE:
            self.toggle_visible()
        elif cmd == M_QUIT:
            self.quit()

    # ---------------- 主循环 ----------------
    def loop(self):
        msg = win.MSG()
        last = time.perf_counter()
        while self.running:
            while win.user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, win.PM_REMOVE):
                if msg.message == 0x0012:  # WM_QUIT
                    self.running = False
                    break
                win.user32.TranslateMessage(ctypes.byref(msg))
                win.user32.DispatchMessageW(ctypes.byref(msg))
            now = time.perf_counter()
            dt = min(0.06, now - last)
            last = now
            if self.pending_menu:
                which, self.pending_menu = self.pending_menu, None
                try:
                    self.handle_menu(which)
                except Exception as e:
                    log_error("menu: %r" % (e,))
                last = time.perf_counter()
                continue
            self.update(dt, now)
            busy = self.state in ("walk", "jump", "pat", "laugh", "eat", "drag", "fall", "land") \
                or self.bubble_img is not None or self.hearts or self.hahas
            if busy:
                frame = 1.0 / 30
            elif self.state == "sleep":
                frame = 1.0 / 10
            else:
                frame = 1.0 / 24
            if self.visible and now - self.last_render >= frame:
                self.render()
                self.last_render = time.perf_counter()
            time.sleep(0.007)


def log_error(msg):
    import traceback
    try:
        os.makedirs(win.CONFIG_DIR, exist_ok=True)
        with open(os.path.join(win.CONFIG_DIR, "error.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("[%Y-%m-%d %H:%M:%S] ") + msg + "\n")
            f.write(traceback.format_exc() + "\n")
    except Exception:
        pass


def main():
    win.init_dpi()
    hmutex = win.kernel32.CreateMutexW(None, False, "NaiwaPetSingleInstance")
    if ctypes.get_last_error() == 183:
        return
    pet = Pet()
    if pet.first_run:
        pet.say("你好呀，我是奶蛙", 3.2)
        if not win.autostart_enabled():
            win.set_autostart(True)
        pet.cfg["size"] = pet.size_key
        win.save_config(pet.cfg)
    pet.loop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_error("fatal: %r" % (e,))
        raise
