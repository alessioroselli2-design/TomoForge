#!/usr/bin/env python3
"""Generate the single Class master base without its baked-in left gold ring.

The 13 approved full HD class emblems are placed dynamically over this CLEAN
raster; all other parts of the original master stay unmodified. No image
generator, per-class crop, second gold border, or record-data changes.
Install Pillow as an OFFLINE tooling dependency (not required to run the app).
"""
from pathlib import Path
from PIL import Image, ImageDraw

ART = Path(__file__).resolve().parents[1] / "public" / "card-art"
SRC = ART / "class-master-approved-v4.webp"
DEST = ART / "class-master-single-ring-v1.webp"


def main():
    original = Image.open(SRC).convert("RGBA")
    if original.size != (1060, 1484):
        raise ValueError(f"unexpected Class master size: {original.size}")
    base = Image.new("RGBA", original.size)
    artist = ImageDraw.Draw(base)
    # Beneath the original 260px diameter gold medal, cover only the engraved
    # ring's inner disc, leaving outer scrollwork, banner, title and gems intact.
    artist.ellipse((34, 3, 274, 243), fill=(54, 8, 16, 255))
    clean = Image.alpha_composite(original, base).convert("RGB")
    clean.save(DEST, format="WEBP", quality=86, method=6)
    print(f"Created {DEST}: {clean.size[0]}x{clean.size[1]}")


if __name__ == "__main__":
    main()
