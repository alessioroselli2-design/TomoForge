#!/usr/bin/env python3
"""Produce alpha-only Class motifs/dice for the already engraved gold master.
Only derived images are generated. Never modify approved reference assets.
"""
from math import hypot
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter

P=Path(__file__).resolve().parents[1]/"public"
CLASSES="barbaro bardo chierico druido guerriero monaco paladino ranger ladro stregone warlock mago artefice".split()
DICE="d4 d6 d8 d10 d12 d20".split()

def save_icon(name):
    src=Image.open(P/"emblemi"/"classi-hd"/f"{name}.webp").convert("RGBA")
    if src.size!=(512,512):raise ValueError(f"Unexpected icon size: {name}")
    src=src.crop((94,94,418,418))
    alpha=Image.new("L",src.size);a=alpha.load();p=src.load()
    for y in range(324):
        for x in range(324):
            r,g,b,opacity=p[x,y]
            rad=hypot(x-161.5,y-161.5)
            falloff=max(0,min(1,(146-rad)/15))
            # Reject the coloured dark source plate and its original gold rim.
            # Keep only central gold/silver/green/blue/purple/red motifs.
            warm=(r>82 and g>51 and r>=1.12*g and g>=1.05*b)
            silver=(r+g+b>322 and min(r,g,b)>=67)
            green=(g>72 and g>1.08*r and g>1.12*b)
            blue=(b>119 and g>58 and b>1.12*r and b>1.06*g)
            violet=(b>115 and r>67 and b>1.13*g and r>1.08*g)
            red=(r>127 and r>1.43*g and r>1.30*b)
            a[x,y]=round(opacity*falloff) if (warm or silver or green or blue or violet or red) else 0
    alpha=alpha.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(.7))
    src.putalpha(ImageChops.multiply(src.getchannel("A"),alpha))
    bounds=alpha.point(lambda v:255 if v>=28 else 0).getbbox()
    if not bounds:raise ValueError("No motif: "+name)
    src=src.crop(bounds)
    out=Image.new("RGBA",(207,145))
    scale=min(198/src.width,139/src.height)
    w,h=round(src.width*scale),round(src.height*scale)
    out.alpha_composite(src.resize((w,h),Image.Resampling.LANCZOS),((207-w)//2,(145-h)//2))
    dest=P/"emblemi"/"classi-core-v1"/f"{name}.webp"
    dest.parent.mkdir(parents=True,exist_ok=True)
    out.save(dest,"WEBP",quality=97,method=6,exact=True)

def save_die(name):
    src=Image.open(P/"card-art"/"class-dice"/f"{name}-premium-v29.webp").convert("RGBA")
    w,h=src.size
    alpha=Image.new("L",(w,h));a=alpha.load();p=src.load()
    for y in range(h):
        for x in range(w):
            r,g,b,opacity=p[x,y]
            rad=hypot((x+.5-w/2)/(w/2),(y+.5-h/2)/(h/2))
            if rad<=.54: strength=1
            else:
                red=max(0,min(1,(r-g-17)/37,(r-b-17)/37))
                strength=red*max(0,min(1,(.83-rad)/.15))
            a[x,y]=round(opacity*strength)
    alpha=alpha.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(.8))
    src.putalpha(ImageChops.multiply(src.getchannel("A"),alpha))
    src=src.resize((192,192),Image.Resampling.LANCZOS)
    dest=P/"card-art"/"class-dice-core-v1"/f"{name}.webp"
    dest.parent.mkdir(parents=True,exist_ok=True)
    src.save(dest,"WEBP",quality=97,method=6,exact=True)

if __name__=="__main__":
    for name in CLASSES:save_icon(name)
    for name in DICE:save_die(name)
    print("Generated alpha-only Class motifs and Class die cores; approved originals unchanged")
