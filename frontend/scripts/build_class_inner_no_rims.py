#!/usr/bin/env python3
"""Build the class *inner-symbol* WebPs, without their original circular rims.

The single approved user Class master (1024x1536) already contains the complete
gold circle and its ruby jewels. The 512px 'classi-hd' sources are full
medallions, not transparent icon-only images. Cropping too wide (previous
source radius 168) leaked a second engraved circle onto the master.

Only rebuild the 13 176px internal assets. Never paint, cover, mask or alter
the approved master or the card data, dice, headings or DOM/CSS positions.
Requires Pillow solely when regenerating the image assets offline.
"""
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1] / "public" / "emblemi"
SOURCE = ROOT / "classi-hd"
DEST = ROOT / "classi-inner"
NAMES = (
    "barbaro bardo chierico druido guerriero monaco paladino ranger ladro "
    "stregone warlock mago artefice"
).split()
SOURCE_RADIUS = 145  # original oversized crop at 168 leaked a second gold ring
OUTPUT_SIZE = 176
SOFT_EDGE_PX = 2

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    alpha = Image.new("L", (OUTPUT_SIZE, OUTPUT_SIZE), 0)
    ImageDraw.Draw(alpha).ellipse(
        (1, 1, OUTPUT_SIZE - 2, OUTPUT_SIZE - 2), fill=255
    )
    alpha = alpha.filter(ImageFilter.GaussianBlur(SOFT_EDGE_PX))

    for name in NAMES:
        src = Image.open(SOURCE / (name + ".webp")).convert("RGBA")
        if src.size != (512, 512):
            raise ValueError(f"Expected 512px original for {name}: {src.size}")
        src = src.crop((
            256 - SOURCE_RADIUS, 256 - SOURCE_RADIUS,
            256 + SOURCE_RADIUS, 256 + SOURCE_RADIUS,
        )).resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.Resampling.LANCZOS)
        src.putalpha(ImageChops.multiply(src.getchannel("A"), alpha))
        dest = DEST / (name + ".webp")
        src.save(dest, "WEBP", quality=93, method=6)
        print(name, dest.stat().st_size)

if __name__ == "__main__":
    main()
