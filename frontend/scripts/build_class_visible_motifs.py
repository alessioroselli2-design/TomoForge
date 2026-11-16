#!/usr/bin/env python3
"""Fit the visible alpha bounds of approved Class motifs into one fixed box.

Output format: exactly 207 x 145 px with a TRANSPARENT background.
These images contain ONLY the inner motif, not the existing medal rim.
The master and every other Class layout field remain unchanged.
"""
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]/"public"/"emblemi"
SOURCE=ROOT/"classi-inner"
DEST=ROOT/"classi-visible"
NAMES=("barbaro bardo chierico druido guerriero monaco paladino ranger "
       "ladro stregone warlock mago artefice").split()
WIDTH,HEIGHT=207,145
ALPHA_THRESHOLD=224

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    for name in NAMES:
        source=Image.open(SOURCE/(name+".webp")).convert("RGBA")
        alpha=source.getchannel("A")
        bounds=alpha.point(lambda value:255 if value>=ALPHA_THRESHOLD else 0).getbbox()
        bounds=bounds or alpha.getbbox()
        if not bounds:
            raise ValueError(f"Missing visible pixels: {name}")
        motif=source.crop(bounds)
        scale=min(WIDTH/motif.width,HEIGHT/motif.height)
        w=max(1,round(motif.width*scale))
        h=max(1,round(motif.height*scale))
        output=Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,0))
        output.alpha_composite(motif.resize((w,h),Image.Resampling.LANCZOS),
                               ((WIDTH-w)//2,(HEIGHT-h)//2))
        dest=DEST/(name+".webp")
        output.save(dest,"WEBP",quality=96,method=6)
        print(f"{name}: bounds={bounds} fitted={w}x{h} canvas={WIDTH}x{HEIGHT}")

if __name__=="__main__":
    main()
