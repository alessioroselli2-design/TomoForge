#!/usr/bin/env python3
"""TomoForge Class artwork v2: one approved gold rim, no stacked medallions.

Always derive from the existing 1024x1536 original Class master,
13 approved 512x512 classi-hd sources and original premium-v29 dice.
Never edit those approved input files or production DB records.
"""
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter

PUBLIC = Path(__file__).resolve().parents[1] / "public"
CLASSES = "barbaro bardo chierico druido guerriero monaco paladino ranger ladro stregone warlock mago artefice".split()
DICE = "d4 d6 d8 d10 d12 d20".split()

# All coordinates are in 1024x1536 source-master pixels, NOT CSS px.
MASTER_ICON_RECT = (61, 39, 190, 190)  # circle inside the engraved upper-left gold ring
MASTER_DIE_RECT = (751, 985, 218, 218)  # faceted gem fills the bottom gold ring

def build_class_emblem(name):
    original = Image.open(PUBLIC / "emblemi" / "classi-hd" / f"{name}.webp").convert("RGBA")
    if original.size != (512, 512):
        raise ValueError(f"{name}: unexpected master icon size {original.size}")
    # Keep the APPROVED colour/background and illustrated emblem as one image.
    # Do not convert it into a floating gold silhouette on the card's red well.
    # Exclude only the outer ornamental ring already engraved into the card.
    inner = original.crop((98,98,414,414)).resize((380,380), Image.Resampling.LANCZOS)
    circle = Image.new("L", (380,380), 0)
    ImageDraw.Draw(circle).ellipse((4,4,376,376), fill=255)
    circle = circle.filter(ImageFilter.GaussianBlur(6))
    inner.putalpha(ImageChops.multiply(inner.getchannel("A"),circle))
    if inner.getchannel("A").getbbox() is None:
        raise ValueError(f"{name}: empty emblem")
    target = PUBLIC / "emblemi" / "classi-medal-inner-v2" / f"{name}.webp"
    target.parent.mkdir(parents=True, exist_ok=True)
    inner.save(target, "WEBP", quality=98, method=6, exact=True)

def build_die_polyhedron(name):
    """Remove ONLY v29's redundant gold ornament, not its approved polyhedron,
    facets, colour or printed number. The static Class master owns the ring.
    """
    original = Image.open(PUBLIC / "card-art" / "class-dice" / f"{name}-premium-v29.webp").convert("RGBA")
    width,height=original.size
    outline={
        "d4":[(128,53),(196,168),(57,168)],
        "d6":[(128,51),(186,84),(185,166),(128,199),(70,166),(70,84)],
        "d8":[(128,55),(196,123),(128,200),(60,123)],
        "d10":[(128,57),(193,89),(190,160),(128,201),(65,161),(62,90)],
        "d12":[(128,58),(197,89),(192,162),(128,204),(63,162),(58,91)],
        "d20":[(128,58),(195,85),(188,166),(128,205),(65,166),(58,85)],
    }
    sx,sy=width/256,height/256
    shape=[(round(x*sx),round(y*sy)) for x,y in outline[name]]
    alpha=Image.new("L",(width,height),0)
    ImageDraw.Draw(alpha).polygon(shape,fill=255)
    alpha=alpha.filter(ImageFilter.GaussianBlur(1.4))
    original.putalpha(ImageChops.multiply(original.getchannel("A"),alpha))
    crop=(round(45*sx),round(40*sy),round(211*sx),round(216*sy))
    core=original.crop(crop).resize((256,256),Image.Resampling.LANCZOS)
    if core.getchannel("A").getbbox() is None:
        raise ValueError(f"{name}: empty die")
    target=PUBLIC / "card-art" / "class-dice-polyhedron-v2" / f"{name}.webp"
    target.parent.mkdir(parents=True,exist_ok=True)
    core.save(target,"WEBP",quality=98,method=6,exact=True)

def write_optical_proofs():
    """Readonly screenshot crop from real master pixels, used to validate art.
    The renderer uses the exact same geometry for Safari and canvas printing.
    """
    import io,base64,json
    master=Image.open(PUBLIC/"card-art"/"class-master-user-20261113.webp").convert("RGBA")
    out=PUBLIC/"_class-art-proof";out.mkdir(parents=True,exist_ok=True)
    fixtures=(("bardo","d8"),("barbaro","d12"),("guerriero","d10"),("druido","d8"),("mago","d6"),("paladino","d10"))
    x,y,w,h=MASTER_ICON_RECT
    dx,dy,dw,dh=MASTER_DIE_RECT
    for name,die in fixtures:
        icon=Image.open(PUBLIC/"emblemi"/"classi-medal-inner-v2"/f"{name}.webp").convert("RGBA")
        jewel=Image.open(PUBLIC/"card-art"/"class-dice-polyhedron-v2"/f"{die}.webp").convert("RGBA")
        image=master.copy()
        image.alpha_composite(icon.resize((w,h),Image.Resampling.LANCZOS),(x,y))
        image.alpha_composite(jewel.resize((dw,dh),Image.Resampling.LANCZOS),(dx,dy))
        emblem=image.crop((0,0,320,300)).convert("RGB")
        dice=image.crop((694,922,1014,1222)).convert("RGB")
        result=Image.new("RGB",(640,300))
        result.paste(emblem,(0,0));result.paste(dice,(320,0))
        stream=io.BytesIO();result.save(stream,"JPEG",quality=90,optimize=True)
        (out/f"{name}-v2.json").write_text(json.dumps({"name":name,"die":die,
          "image_base64":base64.b64encode(stream.getvalue()).decode("ascii")}),encoding="utf8")
    print("Class v2: 13 coloured inner medals, 6 premium polyhedra, 1 original gold master")


def build_full_approved_medals_proof():
    """Compare the actual original full HD medallion and premium v29 die,
    with no more artificial crop/masked/retouched polyhedra."""
    import io, base64, json
    master=Image.open(PUBLIC/"card-art"/"class-master-user-20261113.webp").convert("RGBA")
    out=PUBLIC/"_class-art-proof"
    out.mkdir(parents=True,exist_ok=True)
    samples=(("barbaro","d12"),("bardo","d8"),("guerriero","d10"),("druido","d8"))
    for name,die in samples:
        medal=Image.open(PUBLIC/"emblemi"/"classi-hd"/f"{name}.webp").convert("RGBA")
        dice=Image.open(PUBLIC/"card-art"/"class-dice"/f"{die}-premium-v29.webp").convert("RGBA")
        medal=medal.resize((258,258),Image.Resampling.LANCZOS)
        dice=dice.resize((232,232),Image.Resampling.LANCZOS)
        before=master.copy()
        before.alpha_composite(medal,(28,7))
        before.alpha_composite(dice,(740,967))
        # Remove only the old rings UNDER their replacements. The rest of the
        # border, parchment, heading and stat panel are untouched.
        cleaned=master.copy()
        fill=Image.new("RGBA",cleaned.size,(0,0,0,0))
        fill_draw=ImageDraw.Draw(fill)
        fill_draw.ellipse((34,10,281,258),fill=(70,7,15,255))
        fill_draw.ellipse((738,962,973,1210),fill=(85,10,18,255))
        fade=fill.getchannel("A").filter(ImageFilter.GaussianBlur(2))
        fill.putalpha(fade)
        cleaned=Image.alpha_composite(cleaned,fill)
        cleaned.alpha_composite(medal,(28,7))
        cleaned.alpha_composite(dice,(740,967))
        result=Image.new("RGB",(960,320))
        for i,img in enumerate((master,before,cleaned)):
            t=img.crop((0,0,320,300)).convert("RGB")
            result.paste(t,(i*320,0))
        stream=io.BytesIO()
        result.save(stream,format="JPEG",quality=91,optimize=True)
        (out/f"{name}-full-v3.json").write_text(json.dumps({
            "name":name,"image_base64":base64.b64encode(stream.getvalue()).decode("ascii")
        }),encoding="utf8")
        diceproof=Image.new("RGB",(960,300))
        for i,img in enumerate((master,before,cleaned)):
            t=img.crop((704,929,1024,1229)).convert("RGB")
            diceproof.paste(t,(i*320,0))
        stream=io.BytesIO()
        diceproof.save(stream,format="JPEG",quality=91,optimize=True)
        (out/f"{name}-die-full-v3.json").write_text(json.dumps({
            "name":name,"image_base64":base64.b64encode(stream.getvalue()).decode("ascii")
        }),encoding="utf8")


def build_clean_composition_proof():
    """Alternative full original medals, no old gold layer beneath.
    Parchment overprint masks ONLY the original die socket, and the card's
    original approved outer frame is retained.
    """
    import io,base64,json,math
    master=Image.open(PUBLIC/"card-art"/"class-master-user-20261113.webp").convert("RGBA")
    parchment=master.crop((422,943,708,1229)).resize((280,280),Image.Resampling.LANCZOS)
    texmask=Image.new("L",(280,280),0)
    draw=ImageDraw.Draw(texmask)
    draw.ellipse((9,8,270,272),fill=255)
    texmask=texmask.filter(ImageFilter.GaussianBlur(5))
    out=PUBLIC/"_class-art-proof";out.mkdir(parents=True,exist_ok=True)
    for name,die in (("bardo","d8"),("barbaro","d12"),("guerriero","d10"),("druido","d8")):
        full=master.copy()
        red=Image.new("RGBA",full.size,(0,0,0,0))
        draw=ImageDraw.Draw(red)
        draw.ellipse((37,17,278,258),fill=(73,6,13,255))
        red.putalpha(red.getchannel("A").filter(ImageFilter.GaussianBlur(2)))
        full=Image.alpha_composite(full,red)
        full.paste(parchment,(711,940),texmask)
        medal=Image.open(PUBLIC/"emblemi"/"classi-hd"/f"{name}.webp").convert("RGBA")
        jewel=Image.open(PUBLIC/"card-art"/"class-dice"/f"{die}-premium-v29.webp").convert("RGBA")
        medal=medal.resize((280,280),Image.Resampling.LANCZOS)
        jewel=jewel.resize((248,248),Image.Resampling.LANCZOS)
        full.alpha_composite(medal,(18,-2))
        full.alpha_composite(jewel,(733,959))
        originals=master.copy()
        originals.alpha_composite(medal,(18,-2))
        originals.alpha_composite(jewel,(733,959))
        for label,img,crop in (("medal",full,(0,0,320,300)),
                              ("die",full,(704,929,1024,1229))):
            piece=Image.new("RGB",(640,300))
            piece.paste(master.crop(crop).convert("RGB"),(0,0))
            piece.paste(img.crop(crop).convert("RGB"),(320,0))
            data=io.BytesIO();piece.save(data,format="JPEG",quality=92,optimize=True)
            (out/f"{name}-{label}-v4.json").write_text(json.dumps({
               "name":name,"image_base64":base64.b64encode(data.getvalue()).decode("ascii")
            }),encoding="utf8")
        # Full card proof with actual original outer frame and dynamic-only slots
        shot=full.resize((512,768),Image.Resampling.LANCZOS).convert("RGB")
        data=io.BytesIO();shot.save(data,format="JPEG",quality=85,optimize=True)
        (out/f"{name}-whole-v4.json").write_text(json.dumps({
            "name":name,"image_base64":base64.b64encode(data.getvalue()).decode("ascii")
        }),encoding="utf8")


def build_embedded_class_masters():
    """Bake the exact original full HD emblems and premium-v29 dice into one
    unchanging class master; no CSS/Canvas duplicate decorative layers."""
    import io, base64, json
    base=Image.open(PUBLIC/"card-art"/"class-master-user-20261113.webp").convert("RGBA")
    fill=Image.new("RGBA",base.size,(0,0,0,0))
    ImageDraw.Draw(fill).ellipse((37,17,278,258),fill=(73,6,13,255))
    fill.putalpha(fill.getchannel("A").filter(ImageFilter.GaussianBlur(2)))
    clean=Image.alpha_composite(base,fill)
    texture=base.crop((422,920,702,1250))
    mask=Image.new("L",(280,330),0)
    ImageDraw.Draw(mask).ellipse((8,6,272,324),fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(6))
    clean.paste(texture,(710,920),mask)
    medals={name:Image.open(PUBLIC/"emblemi"/"classi-hd"/f"{name}.webp")
      .convert("RGBA").resize((280,280),Image.Resampling.LANCZOS) for name in CLASSES}
    gems={die:Image.open(PUBLIC/"card-art"/"class-dice"/f"{die}-premium-v29.webp")
      .convert("RGBA").resize((248,248),Image.Resampling.LANCZOS) for die in DICE}
    dest=PUBLIC/"card-art"/"class-composed-v5"
    dest.mkdir(parents=True,exist_ok=True)
    proofs=PUBLIC/"_class-art-proof"
    proofs.mkdir(parents=True,exist_ok=True)
    for name in CLASSES:
        baseClass=clean.copy()
        baseClass.alpha_composite(medals[name],(18,-2))
        for die in [*DICE,"none"]:
            composed=baseClass.copy()
            if die!="none":composed.alpha_composite(gems[die],(733,959))
            composed.save(dest/f"{name}-{die}.webp","WEBP",quality=95,method=6)
            if (name,die) in (("bardo","d8"),("barbaro","d12"),("guerriero","d10"),("druido","d8")):
                pic=composed.resize((512,768),Image.Resampling.LANCZOS).convert("RGB")
                buffer=io.BytesIO();pic.save(buffer,"JPEG",quality=88,optimize=True)
                (proofs/f"{name}-embedded-v5.json").write_text(json.dumps({
                    "name":name,"die":die,
                    "image_base64":base64.b64encode(buffer.getvalue()).decode("ascii")
                }),encoding="utf8")
    print("13 classes x 7 dice variants, one shared Class raster template")

if __name__ == "__main__":
    for klass in CLASSES: build_class_emblem(klass)
    for die in DICE: build_die_polyhedron(die)
    write_optical_proofs()
    build_full_approved_medals_proof()
    build_clean_composition_proof()
    build_embedded_class_masters()
