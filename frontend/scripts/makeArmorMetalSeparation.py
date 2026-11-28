"""Rebuild the armour proof's transparent metal layer from the two approved assets."""

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

FRONTEND = Path(__file__).resolve().parents[1]
PUBLIC = FRONTEND / "public"
MASTER = PUBLIC / "card-art/front-restored-v18/master-armatura-5x7.webp"
BACK = PUBLIC / "dorsi/armi-armature.jpg"
LAYER = PUBLIC / "card-art/proofs/armor-metal-v25.webp"
PALETTE = FRONTEND / "src/lib/armorProofPalette.json"
LUMA = np.array([.2126, .7152, .0722])
# Landmarks traced on a 720 × 1008 view of this specific master.
SCALE = 2040 / 720
PAPER_SEEDS = [(360, 89), (360, 300), (150, 528), (355, 528), (600, 528), (355, 717)]
# Centre, maximum setting radius and radius for the independent red-core check.
FACETS = [
    (30,27,23,17), (689,27,23,17), (21,150,23,17), (699,150,23,17),
    (360,26,23,17), (360,148,23,17), (112,19,16,10), (608,19,16,10),
    (35,90,12,7), (188,90,12,7), (533,90,12,7), (682,90,12,7),
    (112,160,16,10), (608,160,16,10), (21,342,23,17), (699,342,23,17),
    (21,448,23,17), (699,448,23,17), (360,445,23,17), (252,457,12,7),
    (468,457,12,7), (252,546,12,7), (468,546,12,7), (21,557,23,17),
    (699,557,23,17), (360,556,23,17), (30,951,23,17), (690,951,23,17),
    (360,960,23,17),
]


def native_point(x, y):
    return round(y * SCALE), round(x * SCALE)


def connected_core(candidates, x, y, radius):
    cy, cx = native_point(x, y)
    reach = round(radius * SCALE)
    height, width = candidates.shape
    region = np.s_[max(0,cy-reach):min(height,cy+reach+1),
                   max(0,cx-reach):min(width,cx+reach+1)]
    labels, _ = ndimage.label(candidates[region])
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    assert sizes.max() > 18
    return region, ndimage.binary_fill_holes(labels == sizes.argmax())


def paper_panels(red, green):
    # Erosion breaks hairline bridges between the paper shadow and an engraving.
    # Filling the six islands protects enclosed ink, rules and black icons.
    seeds = ndimage.binary_erosion((red > 100) & (green > 60), iterations=3)
    labels, _ = ndimage.label(seeds)
    panels = [labels[native_point(x,y)] for x, y in PAPER_SEEDS]
    assert len(set(panels)) == 6 and 0 not in panels
    paper = ndimage.binary_fill_holes(np.isin(labels, panels))
    return ndimage.binary_dilation(paper, iterations=8)


def jewel_mask(red, green, blue):
    height, width = red.shape
    setting = (green > blue*1.16+13) & (green > red*.37) & (green > 67) & (red > green*.83)
    ruby = (red > green*1.32) & (blue > green*.69+5) & (red > 48)
    facets = Image.new("1", (width, height))
    draw = ImageDraw.Draw(facets)
    theta = np.arange(720)*np.pi/360
    red_cores = np.zeros_like(ruby)
    for x, y, reach, core_radius in FACETS:
        cy, cx = native_point(x, y)
        distance = np.arange(0, reach*SCALE, .5)
        yy = np.rint(cy+np.sin(theta[:,None])*distance).astype(int).clip(0,height-1)
        xx = np.rint(cx+np.cos(theta[:,None])*distance).astype(int).clip(0,width-1)
        hit = setting[yy,xx] & (distance > reach*SCALE*.21)
        edge = hit[:,:-3] & hit[:,3:]
        radius = np.where(edge.any(axis=1), distance[edge.argmax(axis=1)], distance[-1])
        radius = ndimage.median_filter(radius, size=7, mode="wrap") + 1.8
        draw.polygon(list(zip(cx+np.cos(theta)*radius, cy+np.sin(theta)*radius)), fill=1)
        region, core = connected_core(ruby, x, y, core_radius)
        red_cores[region] |= ndimage.binary_dilation(core, iterations=2)
    return np.asarray(facets) | red_cores


def red_discs(green, blue):
    discs = np.zeros_like(green, dtype=bool)
    for x in (112, 608):
        region, core = connected_core((green < 53) & (blue < 60), x, 90, 71)
        yy, xx = np.ogrid[region[0],region[1]]
        seat = ((xx-x*SCALE)/(68*SCALE))**2 + ((yy-90*SCALE)/(63*SCALE))**2
        discs[region] |= (core & (seat < 1.04)) | (seat < .92)
    return ndimage.binary_dilation(discs, iterations=2)


def metal_alpha(source):
    red, green, blue = source.astype("int16").transpose(2,0,1)
    protected = paper_panels(red,green) | jewel_mask(red,green,blue) | red_discs(green,blue)
    warm = (red>68) & (green>51) & (red>green*.88) & (blue<green*.91)
    highlights = (red>170) & (green>152) & (blue<green*1.06) & (red>=green*.93)
    relief = ndimage.binary_dilation((warm|highlights) & ~protected, iterations=4)
    labels, _ = ndimage.label(relief)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    metal = (sizes[labels] > 200) & ~protected
    metal[round(994*SCALE):] = False
    # Feather only inward. Preserve near-black engraving and exterior shadows.
    alpha = np.clip(ndimage.distance_transform_edt(metal)/2, 0, 1)
    alpha *= np.clip((source @ LUMA - 7)/22, 0, 1)
    return np.rint(alpha*255).astype("uint8"), protected


def rear_palette():
    back = np.asarray(Image.open(BACK).convert("RGB"))
    assert back.shape[:2] == (1050,750)
    swatches = Image.new("1",(750,1050))
    draw = ImageDraw.Draw(swatches)
    scrolls = [
        [(72,9),(221,9),(180,21),(108,31),(90,52)],
        [(8,78),(25,92),(55,95),(24,135),(8,142)],
        [(11,188),(43,139),(53,142),(32,180),(10,213)],
    ]
    for polygon in scrolls:
        for flip_x, flip_y in [(False,False),(True,False),(False,True),(True,True)]:
            draw.polygon([(749-x if flip_x else x,1049-y if flip_y else y) for x,y in polygon], fill=1)
    red, green, blue = back.astype(float).transpose(2,0,1)
    samples = back[np.asarray(swatches) & (red>green*1.07) & (green>blue*1.16) & (green>blue+6)]
    light = samples @ LUMA
    levels = np.percentile(light, [2,9,23,43,62,78,91,98,99.7])
    colors = [[0,0,0]] + [
        np.rint(np.median(samples[abs(light-v)<3.5],axis=0)).astype(int).tolist() for v in levels
    ]
    return {"knots":[0,26,53,85,120,154,186,215,241,255], "colors":colors}


def main():
    source = np.asarray(Image.open(MASTER).convert("RGB"))
    assert source.shape[:2] == (2856,2040)
    alpha, protected = metal_alpha(source)
    palette = rear_palette()
    light = source @ LUMA
    colors = np.array(palette["colors"])
    channels = [np.interp(light,palette["knots"],channel) for channel in colors.T]
    pixels = np.dstack([np.rint(c).astype("uint8") for c in channels] + [alpha])
    pixels[alpha == 0] = 0
    Image.fromarray(pixels).save(LAYER, lossless=True, method=5, exact=True)
    decoded = Image.open(LAYER).convert("RGBA")
    assert np.array_equal(np.asarray(decoded), pixels)
    composed = Image.alpha_composite(Image.fromarray(source).convert("RGBA"), decoded).convert("RGB")
    assert np.array_equal(np.asarray(composed)[protected], source[protected])
    PALETTE.write_text(json.dumps(palette,indent=2)+"\n")


if __name__ == "__main__":
    main()
