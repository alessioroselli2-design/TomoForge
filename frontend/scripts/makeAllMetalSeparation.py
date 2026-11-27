"""Extend the approved v25 metal-layer technique, without changing any base art."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
import makeArmorMetalSeparation as v25

PUBLIC=v25.PUBLIC
SRC=PUBLIC/'card-art/front-restored-v18'
OUT=PUBLIC/'card-art/proofs/metal-v26'
OUT.mkdir(exist_ok=True)
PALETTE=json.loads(v25.PALETTE.read_text())
# Coordinates traced on 270x378 views of the corresponding approved master.
def landmarks(points):
    return [(round(x*720/270),round(y*720/270),r,c) for x,y,r,c in points]
def seeds(points):
    return [(round(x*720/270),round(y*720/270)) for x,y in points]
common_top=landmarks([(11,10,22,15),(258,10,22,15),(135,10,22,15),(43,10,14,9),(227,10,14,9),(11,35,12,7),(75,35,12,7),(195,35,12,7),(259,35,12,7),(43,66,14,9),(227,66,14,9),(10,62,22,15),(259,62,22,15),(135,62,22,15)])
class_facets=common_top+landmarks([(10,138,20,13),(259,138,20,13),(10,178,20,13),(259,178,20,13),(135,179,20,13),(94,185,10,6),(174,185,10,6),(94,235,10,6),(174,235,10,6),(10,239,20,13),(259,239,20,13),(135,239,20,13),(11,351,22,15),(259,351,22,15),(135,355,22,15)])
spell_facets=common_top+landmarks([(10,138,20,13),(259,138,20,13),(10,178,20,13),(259,178,20,13),(135,179,20,13),(10,221,20,13),(259,221,20,13),(135,221,20,13),(10,253,20,13),(259,253,20,13),(135,253,20,13),(135,318,18,12),(11,351,22,15),(259,351,22,15),(135,355,22,15)])
monster_facets=landmarks([(10,10,18,12),(260,10,18,12),(135,8,18,12),(42,8,12,7),(228,8,12,7),(11,32,11,6),(74,32,11,6),(196,32,11,6),(259,32,11,6),(42,58,12,7),(228,58,12,7),(10,58,18,12),(260,58,18,12),(135,54,18,12),(10,125,18,12),(259,125,18,12),(10,155,18,12),(259,155,18,12),(135,155,18,12),(10,190,18,12),(259,190,18,12),(10,228,18,12),(259,228,18,12),(135,340,20,13),(14,336,20,13),(256,336,20,13)])
configs={
 'front-master-v17':(seeds([(135,32),(42,173),(133,173),(225,173),(33,207),(73,207),(115,207),(155,207),(194,207),(235,207),(72,245),(196,245),(135,300)]),monster_facets),
 'master-classe-5x7-senza-muscolo-e-anello-20261118':(seeds([(135,35),(135,120),(49,215),(136,215),(218,215),(135,290)]),class_facets),
 'master-incantesimo-5x7-v1':(seeds([(135,35),(135,120),(42,205),(105,205),(160,205),(222,205),(45,238),(135,238),(220,238),(135,285),(135,335)]),spell_facets),
}
# Same layout for the six dedicated category masters; preserve approved Armor exactly.
report=[]
for file in sorted(SRC.glob('*.webp')):
 if file.stem=='master-armatura-5x7':continue
 source=np.array(Image.open(file).convert('RGB'))
 assert source.shape[:2]==(2856,2040)
 r,g,b=source.astype('int16').transpose(2,0,1)
 ps,facets=configs.get(file.stem,(v25.PAPER_SEEDS,v25.FACETS))
 # The v25 technique protects filled parchment islands, including printed ink.
 # Require every seed to lie in a pale connected component, then fill holes.
 labels,_=ndimage.label(ndimage.binary_erosion((r>100)&(g>60),iterations=3))
 ids=[labels[v25.native_point(x,y)] for x,y in ps]
 if 0 in ids:
    # A seed may land on an engraved character or divider. Find nearest paper,
    # restricted to a small neighborhood within the same field.
    for j,k in enumerate(ids):
      if k:continue
      y,x=v25.native_point(*ps[j]); block=labels[y-20:y+21,x-20:x+21]
      vals=block[block>0];assert vals.size,(file.name,ps[j])
      ids[j]=np.bincount(vals).argmax()
 paper=ndimage.binary_dilation(ndimage.binary_fill_holes(np.isin(labels,ids)),iterations=8)
 assert .35<paper.mean()<.88,(file.name,paper.mean())
 # Use the validated v25 radial facet algorithm at the traced positions.
 # For a small missing ruby in a variant, skip only that absent facet.
 ruby=(r>g*1.32)&(b>g*.69+5)&(r>48)
 valid=[]
 for f in facets:
    try:v25.connected_core(ruby,f[0],f[1],f[3]);valid.append(f)
    except AssertionError:pass
 saved=v25.FACETS;v25.FACETS=valid
 try:gems=v25.jewel_mask(r,g,b)
 finally:v25.FACETS=saved
 # Original red disks, adjusting the center for the older monster master.
 if file.stem=='front-master-v17':
    discs=np.zeros_like(g,dtype=bool)
    Y,X=np.ogrid[:g.shape[0],:g.shape[1]]
    for x,y in [(42,32),(228,32)]:
       discs|=((X-x*2040/270)/(22*2040/270))**2+((Y-y*2856/378)/(22*2856/378))**2<1
 else:discs=v25.red_discs(g,b)
 protected=paper|gems|discs
 # Protect deep reds and the illustration on the shared monster master;
 # keep its lava and the original bottom lava intact outside the metal.
 protected|=(r>g*1.8)&(b>g*.8+4)
 if file.stem=='front-master-v17':
    art=Image.new('1',(2040,2856));dr=ImageDraw.Draw(art)
    dr.rounded_rectangle((round(17*2040/270),round(63*2856/378),round(253*2040/270),round(152*2856/378)),radius=55,fill=1)
    protected|=np.asarray(art)
    cutoff=round(350*2856/378)
 elif file.stem in configs:cutoff=round(365*2856/378)
 else:cutoff=round(994*v25.SCALE)
 warm=(r>68)&(g>51)&(r>g*.88)&(b<g*.91)
 highlights=(r>170)&(g>152)&(b<g*1.06)&(r>=g*.93)
 relief=ndimage.binary_dilation((warm|highlights)&~protected,iterations=4)
 lab,_=ndimage.label(relief);sz=np.bincount(lab.ravel());sz[0]=0
 metal=(sz[lab]>200)&~protected
 metal[cutoff:]=False
 light=source@v25.LUMA
 a=np.rint(np.clip(ndimage.distance_transform_edt(metal)/2,0,1)*np.clip((light-7)/22,0,1)*255).astype('uint8')
 assert not a[protected].any()
 pixels=np.dstack([np.rint(np.interp(light,PALETTE['knots'],c)).astype('uint8') for c in np.array(PALETTE['colors']).T]+[a])
 pixels[a==0]=0
 dest=OUT/file.name
 Image.fromarray(pixels).save(dest,lossless=True,method=3,exact=True)
 decoded=Image.open(dest).convert('RGBA')
 assert np.array_equal(np.asarray(decoded),pixels)
 composed=Image.alpha_composite(Image.fromarray(source).convert('RGBA'),decoded).convert('RGB')
 assert np.array_equal(np.asarray(composed)[protected],source[protected])
 assert 100000<np.count_nonzero(a)<1600000,(file.name,np.count_nonzero(a))
 row=dict(file=file.name,panels=len(set(ids)),facets=len(valid),protected=int(protected.sum()),metal=int(np.count_nonzero(a)))
 report.append(row);print(row,flush=True)
 if __import__('os').environ.get('PROOF_THUMBS'):
    composed.thumbnail((270,378));composed.save(Path('/tmp/v26')/(file.stem+'.jpg'),quality=65)
assert len(report)==8
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
