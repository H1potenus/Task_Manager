"""Uygulama simgesini (assets/icon.png ve assets/icon.ico) üretir.

Kullanım:  python tools/make_icon.py
Tasarım: koyu lacivert yuvarlak kare + pomodoro (domates) üzerinde onay işareti
ve çevresinde ilerleme halkası.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

S = 1024  # çalışma çözünürlüğü
OUT = Path(__file__).resolve().parent.parent / "assets"


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vertical_gradient(size, top, bottom):
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        c = lerp(top, bottom, y / (size - 1))
        for x in range(size):
            px[x, y] = c
    return img


def build() -> Image.Image:
    # --- zemin: yuvarlatılmış kare, koyu lacivert degrade
    bg = vertical_gradient(S, (38, 54, 92), (14, 20, 38)).convert("RGBA")
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), radius=230, fill=255)
    base = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    base.paste(bg, (0, 0), mask)

    cx, cy = S // 2, int(S * 0.53)

    # --- ilerleme halkası (iz + dolu yay)
    ring = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ring)
    r_out = 400
    box = (cx - r_out, cy - r_out, cx + r_out, cy + r_out)
    d.arc(box, 0, 360, fill=(255, 255, 255, 38), width=46)
    d.arc(box, -90, 160, fill=(86, 180, 255, 255), width=46)
    # yay uçlarını yuvarla
    for ang in (-90, 160):
        a = math.radians(ang)
        ex = cx + (r_out - 23) * math.cos(a)
        ey = cy + (r_out - 23) * math.sin(a)
        d.ellipse((ex - 23, ey - 23, ex + 23, ey + 23), fill=(86, 180, 255, 255))
    base = Image.alpha_composite(base, ring)

    # --- domates gövdesi (gölge + degrade daire)
    r = 300
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((cx - r, cy - r + 26, cx + r, cy + r + 26), fill=(0, 0, 0, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))
    base = Image.alpha_composite(base, shadow)

    tomato = vertical_gradient(2 * r, (255, 108, 92), (214, 44, 52)).convert("RGBA")
    tmask = Image.new("L", (2 * r, 2 * r), 0)
    ImageDraw.Draw(tmask).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
    base.paste(tomato, (cx - r, cy - r), tmask)

    # --- parlama
    gl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(gl).ellipse((cx - 210, cy - 235, cx - 60, cy - 130), fill=(255, 255, 255, 70))
    base = Image.alpha_composite(base, gl.filter(ImageFilter.GaussianBlur(10)))

    # --- yaprak / sap
    leaf = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(leaf)
    top = cy - r + 8
    green = (62, 190, 120, 255)
    for k in range(5):
        ang = math.radians(-90 + (k - 2) * 38)
        length = 150 if k != 2 else 120
        tip = (cx + length * math.cos(ang) * 1.05, top - 6 + length * math.sin(ang) * 0.6 + 20)
        w = 52
        px_, py_ = -math.sin(ang), math.cos(ang)
        ld.polygon([(cx, top + 8), (cx + px_ * w * 0.5 + (tip[0] - cx) * 0.5, top + 8 + py_ * w * 0.2 + (tip[1] - top - 8) * 0.5),
                    tip,
                    (cx - px_ * w * 0.5 + (tip[0] - cx) * 0.5, top + 8 - py_ * w * 0.2 + (tip[1] - top - 8) * 0.5)],
                   fill=green)
    ld.ellipse((cx - 38, top - 22, cx + 38, top + 40), fill=(40, 150, 92, 255))
    ld.rounded_rectangle((cx - 15, top - 90, cx + 15, top - 10), radius=15, fill=(40, 150, 92, 255))
    base = Image.alpha_composite(base, leaf)

    # --- onay işareti
    chk = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cd = ImageDraw.Draw(chk)
    pts = [(cx - 135, cy + 25), (cx - 40, cy + 120), (cx + 150, cy - 75)]
    cd.line(pts, fill=(255, 255, 255, 255), width=64, joint="curve")
    for p in (pts[0], pts[2]):
        cd.ellipse((p[0] - 32, p[1] - 32, p[0] + 32, p[1] + 32), fill=(255, 255, 255, 255))
    base = Image.alpha_composite(base, chk)
    return base


def main() -> None:
    OUT.mkdir(exist_ok=True)
    img = build()
    img.resize((512, 512), Image.LANCZOS).save(OUT / "icon.png")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    img.save(OUT / "icon.ico", sizes=[(s, s) for s in sizes])
    print("OK:", OUT / "icon.png", OUT / "icon.ico")


if __name__ == "__main__":
    main()
