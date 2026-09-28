"""
Turns assets/face_cutout.png (background already removed) into ASCII art.

Each character cell is matched against the real Consolas glyph shapes plus a
brightness term, so edges (hair outline, eyes, jaw) and tones both survive.
Settings were picked by grid-searching SSIM against the photo, scored on the
portrait rendered at its real size on the card (398x525 px).
Writes assets/ascii.txt (bright pixels -> dense glyphs, for the dark card).

Run locally once (needs Windows' Consolas):  python ascii_portrait.py
"""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = "assets/face_cutout.png"
FONT = "C:/Windows/Fonts/consola.ttf"
FONT_BOLD = "C:/Windows/Fonts/consolab.ttf"
COLS, ROWS = 120, 71
CROP = (470, 215, 1030, 888)           # head + shoulders in the 1200x1200 cutout
FACE = (600, 440, 950, 780)            # skin area; tones are normalised on this so the white shirt can't flatten the face
SUB_W, SUB_H = 4, 8                    # sub-samples per cell used for shape matching
CHARS = [chr(c) for c in range(32, 127) if chr(c) not in "_`"]

SETTINGS = dict(bold=True, norm="body", clahe=1.5, gamma=1.0, density=1.0, lam=6)


def glyph_descriptors(bold=False):
    font = ImageFont.truetype(FONT_BOLD if bold else FONT, 40)
    asc, desc = font.getmetrics()
    w, h = int(round(font.getlength("M"))), asc + desc
    descs = []
    for ch in CHARS:
        im = Image.new("L", (w, h), 0)
        ImageDraw.Draw(im).text((0, 0), ch, font=font, fill=255)
        descs.append(np.asarray(im.resize((SUB_W, SUB_H), Image.BOX), dtype=np.float32).ravel() / 255)
    return np.stack(descs)                                 # (G, SUB_W*SUB_H)


def ink_map(invert, clahe, gamma, norm="body"):
    im = Image.open(SRC).convert("RGBA").crop(CROP)
    alpha = np.asarray(im.split()[3], dtype=np.float32) / 255
    gray = np.asarray(im.convert("L"))
    # local contrast so eyes / nose / mouth survive the downsampling
    gray = cv2.createCLAHE(clipLimit=clahe, tileGridSize=(8, 8)).apply(gray)
    gray = np.asarray(Image.fromarray(gray).filter(ImageFilter.UnsharpMask(radius=3, percent=80, threshold=2)))
    lum = gray.astype(np.float32) / 255
    if norm == "face":
        fx0, fy0, fx1, fy1 = (FACE[0] - CROP[0], FACE[1] - CROP[1], FACE[2] - CROP[0], FACE[3] - CROP[1])
        lo, hi = np.percentile(lum[fy0:fy1, fx0:fx1][alpha[fy0:fy1, fx0:fx1] > 0.5], (1, 99))
    else:
        lo, hi = np.percentile(lum[alpha > 0.5], (2, 98))
    lum = np.clip((lum - lo) / (hi - lo), 0, 1)
    ink = (1 - lum) if invert else lum
    ink = 0.10 + 0.90 * ink ** gamma                       # faint texture keeps the silhouette visible
    ink *= alpha
    edge = Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.FIND_EDGES)
    return np.maximum(ink, np.asarray(edge, dtype=np.float32) / 255 * 0.8)


def to_ascii(ink, glyphs, density, lam):
    img = Image.fromarray((np.clip(ink, 0, 1) * 255).astype(np.uint8))
    img = img.resize((COLS * SUB_W, ROWS * SUB_H), Image.BOX)
    a = np.asarray(img, dtype=np.float32) / 255
    cells = a.reshape(ROWS, SUB_H, COLS, SUB_W).transpose(0, 2, 1, 3).reshape(ROWS * COLS, -1)
    cells *= glyphs.mean(1).max() * density                # map full brightness to the densest glyphs
    d = (cells ** 2).sum(1)[:, None] - 2 * cells @ glyphs.T + (glyphs ** 2).sum(1)[None, :]
    # brightness term: keeps tones right so no single glyph shape takes over
    d += lam * cells.shape[1] * (cells.mean(1)[:, None] - glyphs.mean(1)[None, :]) ** 2
    idx = d.argmin(1).reshape(ROWS, COLS)
    return ["".join(CHARS[i] for i in row).rstrip() for row in idx]


if __name__ == "__main__":
    m = SETTINGS
    ink = ink_map(False, m["clahe"], m["gamma"], m["norm"])
    lines = to_ascii(ink, glyph_descriptors(m["bold"]), m["density"], m["lam"])
    with open("assets/ascii.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"assets/ascii.txt  ({len(lines)} rows)")
