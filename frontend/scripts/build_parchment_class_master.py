#!/usr/bin/env python3
"""Build the neutral parchment Class master from the previous signed-off master.

Only the inner empty illustration area changes. The gold rails, medallion
position and shared stat/description sections remain identical across classes.
Offline-only art generation; no dependencies added to the frontend build.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ART=Path(__file__).resolve().parents[1]/"public"/"card-art"
SOURCE=ART/"class-master-single-ring-v1.webp"
DEST=ART/"class-master-single-ring-parchment-v2.webp"

def main():
    original=Image.open(SOURCE).convert("RGB")
    if original.size != (1060,1484):
        raise ValueError(f"Unexpected master dimensions: {original.size}")
    patch=original.crop((145,968,906,1240)).resize((970,475),Image.Resampling.LANCZOS)
    patch=ImageEnhance.Contrast(patch).enhance(.90)
    mask=Image.new("L",original.size,0)
    ImageDraw.Draw(mask).rounded_rectangle((62,233,998,683),radius=34,fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(5))
    layer=Image.new("RGB",original.size)
    layer.paste(patch,(45,219))
    result=Image.composite(layer,original,mask)
    result.save(DEST,"WEBP",quality=88,method=6)
    print(f"Generated {DEST}: {result.size}")

if __name__=="__main__":
    main()
