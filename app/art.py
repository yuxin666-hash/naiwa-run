"""奶蛙的素材加载与逐帧绘制。"""
import json
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

BODY_H = 1198          # 素材原图高度
INK = (94, 72, 38)     # 气泡文字
CARD = (255, 253, 245, 244)
CARD_LINE = (232, 180, 82)

_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhl.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]


def _font(px):
    for p in _FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, px)
            except Exception:
                pass
    return ImageFont.load_default()


class Sprite:
    """按目标高度缩放好的立绘 + 关键锚点。"""

    def __init__(self, height):
        height = max(60, int(height))
        src_open = Image.open(os.path.join(ASSETS, "frog.png")).convert("RGBA")
        src_closed = Image.open(os.path.join(ASSETS, "frog_closed.png")).convert("RGBA")
        laugh_path = os.path.join(ASSETS, "frog_laugh.png")
        src_laugh = Image.open(laugh_path).convert("RGBA") if os.path.exists(laugh_path) else src_closed
        with open(os.path.join(ASSETS, "meta.json"), encoding="utf-8") as f:
            meta = json.load(f)
        s = height / BODY_H
        w = max(1, round(src_open.width * s))
        self.scale = s
        self.h = height
        self.w = w
        # 留出旋转余量
        pad = max(6, int(height * 0.05))
        self.pad = pad
        size = (w + pad * 2, height + pad * 2)
        canvas = Image.new("RGBA", size, (0, 0, 0, 0))
        canvas.paste(src_open.resize((w, height), Image.LANCZOS), (pad, pad), )
        self.open = canvas
        canvas2 = Image.new("RGBA", size, (0, 0, 0, 0))
        canvas2.paste(src_closed.resize((w, height), Image.LANCZOS), (pad, pad))
        self.closed = canvas2
        canvas3 = Image.new("RGBA", size, (0, 0, 0, 0))
        canvas3.paste(src_laugh.resize((w, height), Image.LANCZOS), (pad, pad))
        self.laugh = canvas3
        # 脚底锚点: 立绘底部中心
        self.anchor = (size[0] / 2.0, float(size[1] - pad))
        self.mouth = (pad + meta["mouth"]["x"] * s, pad + meta["mouth"]["y"] * s)
        self.head_top = (pad + meta["head_top"]["x"] * s, pad + meta["head_top"]["y"] * s)
        self.eye_front = (pad + meta["eyes"]["front"]["cx"] * s,
                          pad + meta["eyes"]["front"]["cy"] * s)

    def shadow(self, strength=1.0):
        sw = int(self.w * 1.25)
        sh = max(6, int(self.w * 0.26))
        img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((2, 2, sw - 3, sh - 3), fill=(60, 48, 22, int(96 * strength)))
        return img.filter(ImageFilter.GaussianBlur(sh * 0.30))


def transform_sprite(img, anchor, target, angle_deg, sx, sy, flip=False):
    """绕脚底锚点做缩放+旋转, 把锚点放到 target。只在包围盒上运算, 保证速度。"""
    w, h = img.size
    ax, ay = anchor
    if flip:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
        ax = w - ax
    th = math.radians(angle_deg)
    c, s = math.cos(th), math.sin(th)
    a00, a01 = c * sx, -s * sy
    a10, a11 = s * sx, c * sy
    det = a00 * a11 - a01 * a10
    if abs(det) < 1e-6:
        return img, (target[0] - ax, target[1] - ay)
    i00, i01 = a11 / det, -a01 / det
    i10, i11 = -a10 / det, a00 / det
    pts = []
    for px, py in ((0, 0), (w, 0), (0, h), (w, h)):
        dx, dy = px - ax, py - ay
        pts.append((a00 * dx + a01 * dy + target[0], a10 * dx + a11 * dy + target[1]))
    x0 = int(math.floor(min(p[0] for p in pts)))
    y0 = int(math.floor(min(p[1] for p in pts)))
    x1 = int(math.ceil(max(p[0] for p in pts)))
    y1 = int(math.ceil(max(p[1] for p in pts)))
    ow, oh = x1 - x0, y1 - y0
    if ow <= 0 or oh <= 0:
        return img, (int(target[0] - ax), int(target[1] - ay))
    tx, ty = target[0] - x0, target[1] - y0
    cx = ax - (i00 * tx + i01 * ty)
    cy = ay - (i10 * tx + i11 * ty)
    out = img.transform((ow, oh), Image.Transform.AFFINE, (i00, i01, cx, i10, i11, cy),
                        resample=Image.BICUBIC)
    return out, (x0, y0)


class Bubble:
    """圆角对话气泡, 2 倍超采样绘制后缩小。"""

    _cache = {}

    @classmethod
    def make(cls, text, font_px=14, max_w=250):
        key = (text, font_px, max_w)
        if key in cls._cache:
            return cls._cache[key]
        S = 2
        font = _font(font_px * S)
        probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
        raw_w = probe.textlength(text, font=font) / S
        box_w = min(max_w, max(38, raw_w + 20))
        lines, cur = [], ""
        for ch in text:
            if ch == "\n":
                lines.append(cur)
                cur = ""
                continue
            if probe.textlength(cur + ch, font=font) / S <= box_w - 20:
                cur += ch
            else:
                lines.append(cur)
                cur = ch
        lines.append(cur)
        line_h = font_px * 1.5
        box_h = line_h * len(lines) + 12
        tail = 9
        pad = 6
        W = int(box_w + pad * 2 + 4)
        H = int(box_h + tail + pad * 2 + 4)
        img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        x0, y0 = pad * S, pad * S
        x1, y1 = (W - pad - 4) * S, (H - pad - tail - 4) * S
        r = 10 * S
        d.rounded_rectangle((x0, y0, x1, y1), radius=r, fill=CARD,
                            outline=CARD_LINE, width=int(1.6 * S))
        cx = (x0 + x1) // 2
        d.polygon([(cx - 6 * S, y1 - 1), (cx + 6 * S, y1 - 1), (cx, y1 + tail * S - 2)],
                  fill=CARD, outline=CARD_LINE, width=int(1.6 * S))
        d.rectangle((cx - 6 * S, y1 - 4 * S, cx + 6 * S, y1 - 1), fill=CARD)
        d.line([(cx - 7 * S, y1 - 1), (cx + 7 * S, y1 - 1)], fill=CARD, width=int(1.6 * S))
        ty = y0 + 6 * S
        for ln in lines:
            tw = probe.textlength(ln, font=font)
            d.text(((x0 + x1 - tw) / 2, ty), ln, font=font, fill=INK)
            ty += line_h * S
        img = img.resize((W, H), Image.LANCZOS)
        cls._cache[key] = img
        if len(cls._cache) > 24:
            cls._cache.pop(next(iter(cls._cache)))
        return img


def heart(size=13):
    S = 3
    s = size * S
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = s * 0.26
    d.ellipse((s * 0.06, s * 0.08, s * 0.06 + 2 * r, s * 0.08 + 2 * r), fill=(246, 118, 138, 240))
    d.ellipse((s - 0.06 * s - 2 * r, s * 0.08, s - 0.06 * s, s * 0.08 + 2 * r), fill=(246, 118, 138, 240))
    d.polygon([(s * 0.04, s * 0.38), (s * 0.96, s * 0.38), (s * 0.5, s * 0.95)], fill=(246, 118, 138, 240))
    d.ellipse((s * 0.22, s * 0.17, s * 0.36, s * 0.31), fill=(255, 235, 238, 150))
    return img.resize((size, size), Image.LANCZOS)


def ha_glyph(size=18):
    """一个圆润的「哈」字贴片, 用于大笑时往头顶飘。"""
    key = ("ha", size)
    img = Bubble._cache.get(key)
    if img is not None:
        return img
    S = 3
    s = size * S
    font = _font(int(s * 0.86))
    # 先单独拿一张字形蒙版, 保证字形本身是实心的
    probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    tw = probe.textlength("哈", font=font)
    bbox = font.getbbox("哈")
    x = (s - tw) / 2
    y = (s - (bbox[3] - bbox[1])) / 2 - bbox[1]
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).text((x, y), "哈", font=font, fill=255)
    # 奶油色光晕: 把蒙版膨胀一圈再轻微模糊
    grow = max(2, int(s * 0.035))
    halo_a = mask.filter(ImageFilter.MaxFilter(grow * 2 + 1)).filter(ImageFilter.GaussianBlur(grow * 0.5))
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    im.paste(Image.new("RGBA", (s, s), (255, 244, 214, 255)), (0, 0), halo_a)
    im.paste(Image.new("RGBA", (s, s), (238, 100, 62, 255)), (0, 0), mask)
    out = im.resize((size, size), Image.LANCZOS)
    Bubble._cache[key] = out
    return out


def cookie(size=18):
    S = 3
    s = size * S
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((s * 0.05, s * 0.08, s * 0.95, s * 0.98), fill=(198, 142, 78, 255))
    d.ellipse((s * 0.08, s * 0.08, s * 0.92, s * 0.90), fill=(224, 170, 102, 255))
    for cx, cy, rr in ((0.30, 0.34, 0.075), (0.62, 0.28, 0.065), (0.55, 0.60, 0.08), (0.28, 0.66, 0.06)):
        d.ellipse((s * (cx - rr), s * (cy - rr), s * (cx + rr), s * (cy + rr)), fill=(108, 72, 40, 255))
    return img.resize((size, size), Image.LANCZOS)
