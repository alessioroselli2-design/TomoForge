import {isGold,isOrnamentRegion,sampleRail,tintGoldRailPixels} from "./frameColorProof";
test("samples the exterior gold rather than interior art",()=>{
 const w=100,h=140,p=new Uint8ClampedArray(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++)p.set(x<8||x>92?[181,115,49,255]:[250,210,40,255],4*(y*w+x));
 const a=sampleRail(p,w,h);
 expect(a.v).toBe(181);
 expect(a.h).toBeCloseTo(30,0);
});
test("only gold on the outer rail changes; rubies, parchment and medallions are protected",()=>{
 const w=100,h=140,p=new Uint8ClampedArray(w*h*4);
 const at=(x,y)=>4*(y*w+x);
 const gold=[245,192,65,255],ruby=[218,20,27,255],paper=[245,220,180,255];
 const keep=[[3,70,ruby],[3,90,paper],[16,10,gold],[83,10,gold],[50,42,gold],[50,80,gold],[5,70,gold]];
 for(const [x,y,c] of keep)p.set(c,at(x,y));
 p.set(gold,at(3,110));
 expect(isGold(...ruby)).toBe(false);
 expect(isOrnamentRegion(.16,.07)).toBe(false);
 const count=tintGoldRailPixels(p,w,h,{h:42,s:.73,v:245},{h:32,s:.73,v:181});
 expect(count).toBeGreaterThan(0);
 for(const [x,y,c] of keep.filter(([x,y])=>x!==5||y!==70))expect(Array.from(p.slice(at(x,y),at(x,y)+4))).toEqual(c);
 expect(p[at(3,110)]).toBeLessThan(245);
});
