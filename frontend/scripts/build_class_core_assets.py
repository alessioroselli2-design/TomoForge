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
    out=Image.new("RGBA",(207,168))
    scale=min(198/src.width,162/src.height)
    w,h=round(src.width*scale),round(src.height*scale)
    out.alpha_composite(src.resize((w,h),Image.Resampling.LANCZOS),((207-w)//2,(168-h)//2))
    dest=P/"emblemi"/"classi-core-v1"/f"{name}.webp"
    dest.parent.mkdir(parents=True,exist_ok=True)
    out.save(dest,"WEBP",quality=97,method=6,exact=True)

def save_die(name):
    """Extract the actual coloured polyhedron, not its gold ornament.
    Every source die retains its original numerals, facets and jewel colours.
    """
    from PIL import ImageDraw
    src=Image.open(P/"card-art"/"class-dice"/f"{name}-premium-v29.webp").convert("RGBA")
    w,h=src.size
    # Coordinates measured against the six approved 256x256 premium sources.
    # No second circular ring is copied into the master socket.
    outlines={
        "d4":[(128,53),(196,168),(57,168)],
        "d6":[(128,51),(186,84),(185,166),(128,199),(70,166),(70,84)],
        "d8":[(128,55),(196,123),(128,200),(60,123)],
        "d10":[(128,57),(193,89),(190,160),(128,201),(65,161),(62,90)],
        "d12":[(128,58),(197,89),(192,162),(128,204),(63,162),(58,91)],
        "d20":[(128,58),(195,85),(188,166),(128,205),(65,166),(58,85)],
    }
    sx,sy=w/256,h/256
    polygon=[(round(x*sx),round(y*sy)) for x,y in outlines[name]]
    mask=Image.new("L",(w,h),0)
    ImageDraw.Draw(mask).polygon(polygon,fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(1.4))
    src.putalpha(ImageChops.multiply(src.getchannel("A"),mask))
    # Crop the removed ornamental perimeter away. The jewel remains
    # proportional and occupies the fixed 56x56 engraving on every Class card.
    box=(round(45*sx),round(40*sy),round(211*sx),round(216*sy))
    src=src.crop(box).resize((192,192),Image.Resampling.LANCZOS)
    dest=P/"card-art"/"class-dice-core-v1"/f"{name}.webp"
    dest.parent.mkdir(parents=True,exist_ok=True)
    src.save(dest,"WEBP",quality=97,method=6,exact=True)

def create_visual_proofs():
    # Pixel-faithful diagnostic of the existing Class master with BOTH true
    # transparent overlays. Static proof is not shipped as an app component.
    import io,base64,json
    master=Image.open(P/"card-art"/"class-master-user-20261113.webp").convert("RGBA")
    pairs=[("bardo","d8"),("barbaro","d12"),("guerriero","d10"),("druido","d8")]
    out=P/"_class-art-proof"
    out.mkdir(parents=True,exist_ok=True)
    for name,die in pairs:
        img=master.copy()
        motif=Image.open(P/"emblemi"/"classi-core-v1"/f"{name}.webp").convert("RGBA")
        jewel=Image.open(P/"card-art"/"class-dice-core-v1"/f"{die}.webp").convert("RGBA")
        img.alpha_composite(motif,(54,54))
        img.alpha_composite(jewel.resize((169,169),Image.Resampling.LANCZOS),(771,1018))
        emblem_area=img.crop((0,0,320,300)).convert("RGB")
        die_area=img.crop((694,922,1014,1222)).convert("RGB")
        combo=Image.new("RGB",(640,300))
        combo.paste(emblem_area,(0,0))
        combo.paste(die_area,(320,0))
        memory=io.BytesIO()
        combo.save(memory,format="JPEG",quality=86,optimize=True)
        (out/f"{name}.json").write_text(json.dumps({"name":name,
            "image_base64":base64.b64encode(memory.getvalue()).decode("ascii")}),encoding="utf-8")

if __name__=="__main__":
    for name in CLASSES:save_icon(name)
    for name in DICE:save_die(name)
    create_visual_proofs()
    print("Generated alpha-only Class motifs and Class die cores; approved originals unchanged")
