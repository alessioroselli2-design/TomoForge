"""Offline, reversible bronze master candidates. No app renderer modifications."""
from pathlib import Path
from PIL import Image
import numpy as np, cv2 as cv
import sys, json
source=Path(sys.argv[1]); out=Path(sys.argv[2]); backpath=Path(sys.argv[3])
out.mkdir(parents=True,exist_ok=True)
back=np.asarray(Image.open(backpath).convert('RGB'))
bh,bw=back.shape[:2]
yy,xx=np.indices((bh,bw))
bhs=cv.cvtColor(back,cv.COLOR_RGB2HSV)
bl=back.astype(np.float32)@np.array([.2126,.7152,.0722],np.float32)
sel=(((xx>bw*.015)&(xx<bw*.065))|((xx>bw*.935)&(xx<bw*.985)))&(yy>bh*.17)&(yy<bh*.84)&(bhs[:,:,0]>=10)&(bhs[:,:,0]<=26)&(bhs[:,:,1]>=65)&(bhs[:,:,1]<=225)&(bl>=28)
assert sel.sum()>100
s=back[sel];l=bl[sel];quant=[]
for q in [5,25,50,75,95]:
 lo,hi=np.percentile(l,[max(0,q-10),min(100,q+10)])
 quant.append(np.median(s[(l>=lo)&(l<=hi)],axis=0))
palette=np.vstack([[0,0,0],[25,14,7],quant[0],quant[1],quant[2],quant[3],quant[4]])
knots=[0,30,70,125,180,225,255]
print('rear palette',np.round(palette).astype(int).tolist(),flush=True)
report=[]
for path in sorted(source.glob('*.webp')):
 im=np.array(Image.open(path).convert('RGB'));h,w=im.shape[:2]
 assert (w,h)==(2040,2856)
 small=np.array(Image.fromarray(im).resize((510,714),Image.Resampling.LANCZOS))
 sh,sw=small.shape[:2]
 dark=(small.max(2)<140).astype(np.uint8)
 walls=cv.dilate(cv.morphologyEx(dark,cv.MORPH_CLOSE,np.ones((5,5),np.uint8)),np.ones((3,3),np.uint8))
 n,labels,stats,_=cv.connectedComponentsWithStats(1-walls,connectivity=4)
 paper=np.zeros((sh,sw),np.uint8)
 count=0
 for i in range(1,n):
  x,y,ww,hh,area=stats[i]
  if area<1200 or x<sw*.025 or x+ww>sw*.98 or y<sh*.01 or y+hh>sh*.97:continue
  comp=(labels==i)
  # Only pale parchment panels (or protected medallion interiors). Fill every
  # enclosed hole, so printed black labels and icons remain exact.
  rgb=np.median(small[comp],axis=0)
  if rgb[0]<180 or rgb[1]<95:continue
  contours,_=cv.findContours(comp.astype(np.uint8),cv.RETR_EXTERNAL,cv.CHAIN_APPROX_SIMPLE)
  cv.drawContours(paper,contours,-1,255,-1)
  count+=1
 assert count>=5,(path.name,count)
 paper=cv.dilate(paper,np.ones((3,3),np.uint8))
 protect=np.asarray(Image.fromarray(paper).resize((w,h),Image.Resampling.NEAREST))>0
 hsv=cv.cvtColor(im,cv.COLOR_RGB2HSV)
 # Rubies and red medallion fields, independently from the gold outer rings.
 # Fill enclosed white gemstone glints at 510px, then protect red at full size.
 smh=cv.cvtColor(small,cv.COLOR_RGB2HSV)
 red=((smh[:,:,0]<=9)|(smh[:,:,0]>=161))&(smh[:,:,1]>110)&(smh[:,:,2]>95)
 red=cv.morphologyEx(red.astype(np.uint8),cv.MORPH_CLOSE,np.ones((3,3),np.uint8))
 n,lab,st,_=cv.connectedComponentsWithStats(red,connectivity=8)
 gems=np.zeros_like(paper)
 for i in range(1,n):
  x,y,ww,hh,area=st[i]
  if area<4 or ww>sw*.24 or hh>sh*.19:continue
  cc,_=cv.findContours((lab==i).astype(np.uint8),cv.RETR_EXTERNAL,cv.CHAIN_APPROX_SIMPLE)
  for c in cc:
   cv.drawContours(gems,[cv.convexHull(c)],-1,255,-1)
 # Include disk interiors but not the golden rims around the two medallions.
 for cx in (.158,.841):
  cv.ellipse(gems,(round(cx*sw),round(.09*sh)),(round(.086*sw),round(.0615*sh)),0,0,360,255,-1)
 protect|=np.asarray(Image.fromarray(gems).resize((w,h),Image.Resampling.NEAREST))>0
 protect|=((hsv[:,:,0]<=8)|(hsv[:,:,0]>=162))&(hsv[:,:,1]>120)&(hsv[:,:,2]>95)
 # Keep the lava illustration and the existing lower lava band.
 Y,X=np.indices((h,w),dtype=np.float32);X/=w;Y/=h
 if path.stem=='front-master-v17':
  protect|=(X>.067)&(X<.933)&(Y>.162)&(Y<.398)
  protect|=Y>.94
 else:protect|=Y>.979
 v=im.astype(np.float32)
 light=v@np.array([.2126,.7152,.0722],np.float32)
 metal=np.stack([np.interp(light,knots,palette[:,k]) for k in range(3)],axis=-1)
 distance=cv.distanceTransform((~protect).astype(np.uint8),cv.DIST_L2,3)
 a=np.clip(distance/3,0,1);a=a*a*(3-2*a)
 # Dark ink and deep shadows are not tinted, even outside the panel mask.
 a*=np.clip((light-22)/18,0,1)
 res=np.round(v*(1-a[:,:,None])+metal*a[:,:,None]).clip(0,255).astype(np.uint8)
 assert np.array_equal(res[protect],im[protect])
 dest=out/path.name
 Image.fromarray(res).save(dest,'WEBP',lossless=True,method=3)
 assert np.array_equal(np.array(Image.open(dest).convert('RGB')),res)
 changed=int(np.count_nonzero(np.any(res!=im,axis=2)))
 assert 100000<changed<2200000,(path.name,changed)
 report.append(dict(name=path.name,panels=count,protected=int(protect.sum()),changed=changed,bytes=dest.stat().st_size))
 print(report[-1],flush=True)
(out/'report.json').write_text(json.dumps(report,indent=2))
assert len(report)==9,len(report)
