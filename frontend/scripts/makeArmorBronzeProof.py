from PIL import Image
import numpy as np, cv2 as cv
from pathlib import Path
import sys
root=Path(sys.argv[1])
im=np.array(Image.open(root/'front.webp').convert('RGB'))
h,w=im.shape[:2]
mask=np.array(Image.open(root/'mask.png').convert('L').resize((w,h),Image.Resampling.NEAREST))>0
# Protect gem cores at their actual source coordinates, including antialiased
# highlights and pink/red reflections. Do not touch either upper medallion.
hsv=cv.cvtColor(im,cv.COLOR_RGB2HSV)
Y,X=np.indices((h,w),dtype=np.float32);X/=w;Y/=h
ruby=((hsv[:,:,0]<9)|(hsv[:,:,0]>158))&(hsv[:,:,1]>105)&(hsv[:,:,2]>120)
near=np.zeros((h,w),bool)
centers=[(x,y) for x in [.04,.96] for y in [.026,.157,.339,.445,.548,.951]]+[(.5,.026),(.5,.153),(.5,.445),(.5,.55),(.5,.951),(.333,.454),(.666,.454),(.333,.549),(.666,.549)]
for x,y in centers:near|=(abs(X-x)<.035)&(abs(Y-y)<.025)
mask |= ruby&near
mask |= Y>.975
# Sample actual rear metal; the ramp is intentionally continuous across every
# original gold highlight and shadow rather than selecting isolated yellow hues.
back=np.array(Image.open(root/'back.jpg').convert('RGB').crop((6,7,744,1040)))
bh,bw=back.shape[:2]; by,bx=np.indices((bh,bw));bhs=cv.cvtColor(back,cv.COLOR_RGB2HSV)
bl=back.astype(np.float32)@np.array([.2126,.7152,.0722],np.float32)
edge=(((bx>bw*.008)&(bx<bw*.067))|((bx>bw*.933)&(bx<bw*.992)))&(by>bh*.17)&(by<bh*.84)
sel=edge&(bhs[:,:,0]>=10)&(bhs[:,:,0]<=26)&(bhs[:,:,1]>=65)&(bhs[:,:,1]<=225)&(bl>=28)
samples=back[sel];ls=bl[sel]
assert len(samples)>100
quant=[]
for q in [5,25,50,75,95]:
 lo,hi=np.percentile(ls,[max(0,q-10),min(100,q+10)])
 quant.append(np.median(samples[(ls>=lo)&(ls<=hi)],axis=0))
pal=np.vstack([[0,0,0],[25,14,7],quant[0],quant[1],quant[2],quant[3],quant[4]])
knots=[0,30,70,125,180,225,255]
v=im.astype(np.float32);light=v@np.array([.2126,.7152,.0722],np.float32)
metal=np.stack([np.interp(light,knots,pal[:,k]) for k in range(3)],axis=-1)
# Transition confined to the metallic side; every masked pixel is identical.
distance=cv.distanceTransform((~mask).astype(np.uint8),cv.DIST_L2,3)
a=np.clip(distance/4,0,1);a=a*a*(3-2*a)
out=np.round(v*(1-a[:,:,None])+metal*a[:,:,None]).clip(0,255).astype(np.uint8)
assert np.array_equal(out[mask],im[mask])
changed=int(np.count_nonzero(np.any(out!=im,axis=2)))
assert 500000<changed<1400000,changed
Image.fromarray(out).save(root/'armor-bronze-v23.webp',format='WEBP',lossless=True,method=3)
check=np.array(Image.open(root/'armor-bronze-v23.webp').convert('RGB'))
assert np.array_equal(out,check)
print('palette',np.round(pal).astype(int).tolist(),'protected',int(mask.sum()),'changed',changed,'size', (root/'armor-bronze-v23.webp').stat().st_size)
thumb=Image.fromarray(out);thumb.thumbnail((250,350));thumb.save(root/'thumb.jpg',quality=65)
data=(root/'thumb.jpg').read_bytes()
for i in range(0,len(data),1200):(root/('chunk'+str(i//1200))).write_bytes(data[i:i+1200])
print('chunks',(len(data)+1199)//1200)
