"""从闭眼素材生成「张嘴大笑」素材: 抹掉原嘴线, 画一张张开的嘴。

只在原分辨率(597x1198)上做一次, 输出 assets/frog_laugh.png。
"""
import math
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

# 原素材坐标: 嘴线从 (147,129) 到 (207,133), 嘴角在右
MX0, MY0 = 146.0, 128.5
MX1, MY1 = 208.0, 133.0
S = 4                     # 超采样倍数
W, H = 110, 78
OX, OY = 138.0, 116.0     # 小画布左上角对应的原图坐标


def lerp(a, b, t):
    return a + (b - a) * t


def to_px(x, y):
    return ((x - OX) * S, (y - OY) * S)


def mouth_path(depth=33.0):
    top, bot = [], []
    n = 44
    for i in range(n + 1):
        t = i / n
        x = lerp(MX0, MX1, t)
        y = lerp(MY0, MY1, t)
        d = depth * (math.sin(math.pi * t) ** 0.62)
        top.append(to_px(x, y))
        bot.append(to_px(x, y + d))
    return top, bot


def main():
    base = Image.open(os.path.join(ASSETS, "frog_closed.png")).convert("RGBA")

    # 1) 原嘴线就在嘴型上沿, 不额外补皮肤, 只把这条线轻微柔化
    line_zone = Image.new("L", base.size, 0)
    ImageDraw.Draw(line_zone).polygon(
        [(170, 122), (214, 122), (214, 140), (170, 140)], fill=255)
    line_zone = line_zone.filter(ImageFilter.GaussianBlur(3.0))
    blurred = base.filter(ImageFilter.GaussianBlur(1.6))
    base = Image.composite(blurred, base, line_zone)

    # 2) 画嘴
    img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    top, bot = mouth_path()
    d.polygon(top + bot[::-1], fill=(88, 48, 42, 255))

    # 上颚阴影, 让口腔有纵深
    up2 = []
    for i in range(len(top)):
        t = i / (len(top) - 1)
        x = lerp(MX0, MX1, t)
        y = lerp(MY0, MY1, t) + 9.5 * (math.sin(math.pi * t) ** 0.55)
        up2.append(to_px(x, y))
    d.polygon(top + up2[::-1], fill=(50, 25, 23, 255))

    # 舌头: 先画, 再用嘴型做蒙版裁掉溢出
    tongue = Image.new("RGBA", img.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(tongue)
    tcx = to_px(lerp(MX0, MX1, 0.50), 0)[0]
    ty0 = to_px(0, lerp(MY0, MY1, 0.50) + 15.5)[1]
    td.ellipse((tcx - 15.5 * S, ty0, tcx + 15.5 * S, ty0 + 17.0 * S),
               fill=(198, 108, 102, 255))
    # 舌面高光
    td.ellipse((tcx - 9.0 * S, ty0 + 1.0 * S, tcx + 6.0 * S, ty0 + 5.0 * S),
               fill=(216, 132, 124, 255))
    clip = Image.new("L", img.size, 0)
    ImageDraw.Draw(clip).polygon(top + bot[::-1], fill=255)
    clip = clip.filter(ImageFilter.GaussianBlur(0.6 * S))
    img = Image.alpha_composite(img, Image.composite(
        tongue, Image.new("RGBA", img.size, (0, 0, 0, 0)), clip))

    # 上唇边缘一道浅色高光, 显得有厚度
    lip = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(lip)
    hi = [(x, y - 1.6) for x, y in top]
    ld.line(hi, fill=(255, 208, 122, 90), width=int(1.7 * S), joint="curve")
    img = Image.alpha_composite(img, lip)

    img = img.resize((W, H), Image.LANCZOS)

    # 3) 叠到脸上: 只在嘴附近的皮肤内生效, 边缘羽化
    mouth = Image.new("RGBA", base.size, (0, 0, 0, 0))
    mouth.paste(img, (int(OX), int(OY)), img)
    region = Image.new("L", base.size, 0)
    ImageDraw.Draw(region).rectangle((136, 116, 214, 172), fill=255)
    region = region.filter(ImageFilter.GaussianBlur(1.6))
    region = ImageChops.multiply(region, base.getchannel("A"))
    base = Image.alpha_composite(
        base, Image.composite(mouth, Image.new("RGBA", base.size, (0, 0, 0, 0)), region))

    out = os.path.join(ASSETS, "frog_laugh.png")
    base.save(out)
    print("saved", out, base.size)


if __name__ == "__main__":
    main()
