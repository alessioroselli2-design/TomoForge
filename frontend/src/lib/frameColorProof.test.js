import {sampleBackGold,isMetalGold,traceArmorMetal,tintArmorMetal} from "./frameColorProof";
test("samples the gold of the reverse edge, not the central illustration",()=>{
 const w=100,h=140,p=new Uint8ClampedArray(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++)p.set(x<8||x>92?[181,115,49,255]:[250,210,40,255],4*(y*w+x));
 expect(sampleBackGold(p,w,h).v).toBe(181);
});
test("traced engraved contour excludes paper, rubies and medallions",()=>{
 const w=200,h=280,p=new Uint8ClampedArray(w*h*4);
 const gold=[252,235,54,255],paper=[254,210,95,255],dark=[30,15,3,255],ruby=[220,15,25,255];
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  p.set(x<7||x>w-8?gold:x<10||x>w-11?dark:paper,4*(y*w+x));
 }
 const at=(x,y)=>4*(y*w+x);
 p.set(ruby,at(4,140));p.set(gold,at(32,20));p.set(gold,at(165,20));
 const orig=p.slice(),mask=traceArmorMetal(orig,w,h);
 expect(mask(4,170)).toBe(true);expect(mask(12,170)).toBe(false);
 expect(isMetalGold(...ruby)).toBe(false);
 const count=tintArmorMetal(p,orig,w,h,{h:32,s:.73,v:181});
 expect(count).toBeGreaterThan(0);
 expect(p[at(4,170)]).toBeLessThan(200);
 for(const [x,y] of [[4,140],[12,170],[32,20],[165,20],[100,120]])expect(Array.from(p.slice(at(x,y),at(x,y)+4))).toEqual(Array.from(orig.slice(at(x,y),at(x,y)+4)));
});
