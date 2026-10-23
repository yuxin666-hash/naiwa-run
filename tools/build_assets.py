"""把 奶蛙-clean.png 加工成桌宠可用的透明素材。
产出:
  assets/frog.png        透明背景, 统一比例(原始像素)
  assets/frog_closed.png 闭眼版本(眨眼/睡觉用)
  assets/meta.json       眼睛/嘴/头顶等关键坐标(相对裁剪后的图)
  assets/tray.ico        托盘图标
"""
import json, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "奶蛙-clean.png")
OUT = os.path.join(ROOT, "assets")
os.makedirs(OUT, exist_ok=True)

im = Image.open(SRC).convert("RGB")
W, H = im.size
arr = np.asarray(im).astype(np.float32)

# ---------- 1. 背景连通区域(从四边泛洪) ----------
bg = np.array([247, 227, 198], dtype=np.float32)
dist = np.sqrt(((arr - bg) ** 2).sum(2))
# 背景判定: 既接受纯背景色, 也接受"背景色按比例变暗"的投影区域(两腿之间的暗奶油色)
ratio = arr / bg
rspread = ratio.max(2) - ratio.min(2)
rmean = ratio.mean(2)
bgish = ((dist < 26) | ((rspread < 0.15) & (rmean > 0.55) & (rmean < 1.10)))
similar = bgish.astype(np.uint8) * 255
sim_img = Image.frombytes("L", (W, H), similar.tobytes())
# 用 floodfill 只吃掉与边界连通的背景; 肚皮那块奶油色不与边界相连, 会被保留
px = sim_img.load()
stack = [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)]
seen = bytearray(W * H)
while stack:
    x, y = stack.pop()
    i = y * W + x
    if seen[i]:
        continue
    seen[i] = 1
    if px[x, y] != 255:
        continue
    px[x, y] = 128
    if x > 0: stack.append((x - 1, y))
    if x < W - 1: stack.append((x + 1, y))
    if y > 0: stack.append((x, y - 1))
    if y < H - 1: stack.append((x, y + 1))

outside = np.asarray(sim_img, "L") == 128
core = ~outside
print("outside ratio", outside.mean())

# ---------- 2. 柔化 alpha + 颜色外扩(消除奶油色描边) ----------
mask = (core.astype(np.uint8) * 255)
mimg = Image.fromarray(mask, "L")
alpha = mimg.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.1))

inside = core.copy()
work = arr.copy()
for _ in range(10):
    grew = inside.copy()
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)):
        src = np.roll(np.roll(work, dy, axis=0), dx, axis=1)
        srci = np.roll(np.roll(inside, dy, axis=0), dx, axis=1)
        take = (~grew) & srci
        work[take] = src[take]
        grew |= take
    inside = grew

rgba = np.dstack([np.clip(work, 0, 255).astype(np.uint8), np.asarray(alpha, np.uint8)])
frog = Image.fromarray(rgba, "RGBA")

# 去掉脚下的接触阴影(灰褐色, 会在深色桌面上显脏): 底部 40px 内低饱和度暗块
a = np.asarray(frog).astype(np.float32)
h, w = a.shape[:2]
bottom = np.zeros((h, w), bool)
bottom[h - 46:, :] = True
r, g, b = a[..., 0], a[..., 1], a[..., 2]
mx = a[..., :3].max(2); mn = a[..., :3].min(2)
sat = (mx - mn) / np.maximum(mx, 1)
shadowish = bottom & (sat < 0.42) & (mx < 215) & (mx > 90)
print("shadow px", shadowish.sum())
a[..., 3] = np.where(shadowish, 0, a[..., 3])
frog = Image.fromarray(a.astype(np.uint8), "RGBA")

# ---------- 3. 裁到内容边界 ----------
bbox = frog.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
print("bbox", bbox)
frog = frog.crop(bbox)
fw, fh = frog.size
print("frog size", frog.size)

def T(x, y):
    return (x - bbox[0], y - bbox[1])

eyes = {
    "front": {"cx": 438 - bbox[0], "cy": 233 - bbox[1], "rx": 35, "ry": 32},
    "far": {"cx": 356 - bbox[0], "cy": 240 - bbox[1], "rx": 13, "ry": 19},
}

# ---------- 4. 闭眼版本 ----------
closed = frog.copy()
fa = np.asarray(frog).astype(np.float32)
yy, xx = np.mgrid[0:fh, 0:fw]
body_alpha = Image.fromarray(fa[..., 3].astype(np.uint8))
S = 4
for key, e in eyes.items():
    cx, cy, rx, ry = e["cx"], e["cy"], e["rx"], e["ry"]
    # 采样眼睛周围一圈皮肤色(排除透明像素和过暗的眼线)
    d = np.sqrt(((xx - cx) / (rx + 1.0)) ** 2 + ((yy - cy) / (ry + 1.0)) ** 2)
    ring = (d > 1.45) & (d < 2.0) & (fa[..., 3] > 250)
    cols = fa[ring][:, :3]
    cols = cols[cols.mean(1) > 120]
    med = np.median(cols, axis=0) if len(cols) else np.array([250, 205, 80])
    # 眼皮底色: 先用环采样色盖住眼球, 再取局部低频光影, 保证和周围皮肤无缝
    pad = int(max(rx, ry) * 0.55) + 6
    w_, h_ = int(rx * 2 + pad * 2), int(ry * 2 + pad * 2)
    px0, py0 = int(cx - rx - pad), int(cy - ry - pad)
    ex = int(max(rx, ry) * 2.6)
    wx0, wy0 = max(0, px0 - ex), max(0, py0 - ex)
    win = frog.crop((wx0, wy0, min(fw, px0 + w_ + ex), min(fh, py0 + h_ + ex)))
    dw = ImageDraw.Draw(win)
    ox, oy = px0 - wx0, py0 - wy0
    dw.ellipse((ox + 1, oy + 1, ox + w_ - 2, oy + h_ - 2),
               fill=tuple(int(v) for v in med) + (255,))
    win = win.filter(ImageFilter.GaussianBlur(max(rx, ry) * 0.75))
    patch = win.crop((ox, oy, ox + w_, oy + h_))
    m = Image.new("L", (w_, h_), 0)
    inset = max(3.0, pad * 0.42)
    ImageDraw.Draw(m).ellipse((inset, inset, w_ - inset, h_ - inset), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(inset * 0.6))
    body = body_alpha.crop((px0, py0, px0 + w_, py0 + h_))
    closed.paste(patch, (px0, py0), ImageChops.multiply(m, body))

    # 眼线(4 倍超采样, 保持平滑)
    lw, lh = int(w_ * S), int(h_ * S)
    lid = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lid)
    ocx, ocy = lw / 2.0, lh / 2.0
    pts, pts2 = [], []
    for i in range(29):
        t = i / 14.0 - 1.0
        px_ = ocx + t * rx * 0.78 * S
        py_ = ocy + (0.5 + 4.6 * (1 - t * t)) * S
        pts.append((px_, py_))
        pts2.append((px_, py_ + ry * 0.13 * S))
    dl.line(pts2, fill=tuple(int(min(255, v * 1.14)) for v in med) + (255,),
            width=int(max(1.6, ry * 0.09) * S), joint="curve")
    dl.line(pts, fill=(116, 86, 54, 255), width=int(max(2.0, ry * 0.13) * S), joint="curve")
    lid = lid.resize((w_, h_), Image.LANCZOS)
    body = body_alpha.crop((px0, py0, px0 + w_, py0 + h_))
    lid.putalpha(ImageChops.multiply(lid.getchannel("A"), body))
    closed.alpha_composite(lid, (px0, py0))

closed.save(os.path.join(OUT, "frog_closed.png"))
frog.save(os.path.join(OUT, "frog.png"))

# ---------- 5. 托盘图标 ----------
head = frog.crop((int(300 - bbox[0]), int(150 - bbox[1]),
                  int(560 - bbox[0]), int(410 - bbox[1])))
side = max(head.size)
sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
sq.paste(head, ((side - head.size[0]) // 2, (side - head.size[1]) // 2))
cmask = Image.new("L", (side * 4, side * 4), 0)
ImageDraw.Draw(cmask).ellipse((6, 6, side * 4 - 6, side * 4 - 6), fill=255)
cmask = cmask.resize((side, side), Image.LANCZOS)
icon = sq.copy()
icon.putalpha(Image.composite(sq.getchannel("A"), Image.new("L", (side, side), 0), cmask))
icon.save(os.path.join(OUT, "tray.ico"),
          sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128)])
icon.resize((128, 128), Image.LANCZOS).save(os.path.join(OUT, "tray.png"))

meta = {
    "size": [fw, fh],
    "eyes": eyes,
    "mouth": {"x": 405 - bbox[0], "y": 296 - bbox[1]},
    "head_top": {"x": 445 - bbox[0], "y": 170 - bbox[1]},
    "feet_y": fh,
}
with open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

# ---------- 6. 预览图: 深/浅背景各一张 ----------
for name, color in (("preview_dark", (38, 40, 46)), ("preview_light", (238, 238, 236))):
    canvas = Image.new("RGB", (fw * 2 + 60, fh + 40), color)
    canvas.paste(frog, (30, 20), frog)
    canvas.paste(closed, (fw + 30, 20), closed)
    canvas.save(os.path.join(ROOT, ".work", name + ".png"))
print("done")
