import {reverseAccent,isOrnamentRegion,tintOrnamentPixels} from "./frameColorProof";
test("actual reverse color determines the accent",()=>{
 const p=new Uint8ClampedArray(40*40*4);
 for(let i=0;i<p.length;i+=4)p.set([15,160,255,255],i);
 const a=reverseAccent(p,40,40);
 expect(a.h).toBeGreaterThan(190);expect(a.h).toBeLessThan(220);
});
test("art, both upper emblems and lower dice are protected",()=>{
 expect(isOrnamentRegion(.16,.10,"class")).toBe(false);
 expect(isOrnamentRegion(.83,.10,"spell")).toBe(false);
 expect(isOrnamentRegion(.5,.3,"monster")).toBe(false);
 expect(isOrnamentRegion(.83,.76,"class")).toBe(false);
 expect(isOrnamentRegion(.03,.6,"class")).toBe(true);
});
test("tints ruby but not gold, parchment or the protected image",()=>{
 const w=100,h=140,p=new Uint8ClampedArray(w*h*4);
 const at=(x,y)=>4*(y*w+x);
 p.set([220,20,30,255],at(3,60));
 p.set([220,160,40,255],at(4,60));
 p.set([245,220,180,255],at(5,60));
 p.set([220,20,30,255],at(50,42));
 tintOrnamentPixels(p,w,h,{h:205,s:.85},"monster");
 expect(p[at(3,60)+2]).toBeGreaterThan(p[at(3,60)]);
 expect(Array.from(p.slice(at(4,60),at(4,60)+4))).toEqual([220,160,40,255]);
 expect(Array.from(p.slice(at(5,60),at(5,60)+4))).toEqual([245,220,180,255]);
 expect(Array.from(p.slice(at(50,42),at(50,42)+4))).toEqual([220,20,30,255]);
});
