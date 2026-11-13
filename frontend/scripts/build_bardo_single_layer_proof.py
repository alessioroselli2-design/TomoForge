#!/usr/bin/env python3
"""Rebuild isolated Bardo proof from original repository assets only.

The user-approved reference screenshot is used for visual comparison, NEVER
pasted into this master. No CSS crop, duplicate medal or per-class scaling.
Only the /prova-classi Bardo selection uses the generated image; all production
record mapping, other classes, borders, dice and export logic remain unchanged.
Pillow is an offline preparation dependency, not an app build requirement.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / "public"
MASTER = ROOT / "card-art/class-master-approved-v4.webp"
ICON = ROOT / "emblemi/classi-hd/bardo.webp"
OUTPUT = ROOT / "card-art/bardo-integrated-proof-v1.webp"

def main():
    base = Image.open(MASTER).convert("RGBA")
    emblem = Image.open(ICON).convert("RGBA")
    assert base.size == (1060, 1484) and emblem.size == (512, 512)
    base.alpha_composite(emblem.resize((280, 280), Image.Resampling.LANCZOS), (17, 0))
    base.convert("RGB").save(OUTPUT, format="WEBP", quality=91, method=6)
    print(OUTPUT, OUTPUT.stat().st_size)

if __name__ == "__main__":
    main()
