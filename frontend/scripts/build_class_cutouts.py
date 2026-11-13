#!/usr/bin/env python3
"""Regenerate the 13 transparent inner-Class motifs from the original HD assets.

This is an offline asset-preparation script, not a web-build dependency.
Run from the repository root after installing Pillow: python -m pip install pillow
then python frontend/scripts/build_class_cutouts.py

The original approved full medals are never overwritten. The class card owns a
single engraved rim; this generates only central artwork, with identical crop,
alignment, opacity feather and pixel dimensions for every class.
"""
from math import hypot
from pathlib import Path
from PIL import Image

FRONTEND = Path(__file__).resolve().parents[1]
SOURCE = FRONTEND / "public/emblemi/classi-hd"
DEST = FRONTEND / "public/emblemi/classi-cutout"
CLASSES = ("barbaro", "bardo", "chierico", "druido", "guerriero",
           "monaco", "paladino", "ranger", "ladro", "stregone",
           "warlock", "mago", "artefice")
SIZE = 512
SOURCE_CROP = (106, 106, 406, 406)  # keep just the artwork, not the gold rim


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    for name in CLASSES:
        image = Image.open(SOURCE / f"{name}.webp").convert("RGBA")
        if image.size != (SIZE, SIZE):
            raise ValueError(f"{name}: expected a 512x512 approved asset")
        image = image.crop(SOURCE_CROP).resize((SIZE, SIZE), Image.Resampling.LANCZOS)
        pixels = image.load()
        for y in range(SIZE):
            for x in range(SIZE):
                radius = hypot(x - 255.5, y - 255.5)
                feather = 1.0 if radius <= 212 else max(0.0, min(1.0, (248-radius)/36))
                r, g, b, alpha = pixels[x, y]
                pixels[x, y] = (r, g, b, int(alpha * feather))
        image.save(DEST / f"{name}.webp", "WEBP", quality=74, method=6)
        print(f"Generated {name}: 512x512 / single transparent motif")


if __name__ == "__main__":
    main()
