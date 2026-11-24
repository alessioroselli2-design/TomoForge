import {exteriorAlpha,frontMaskSource,traceOuterRail,perimeterPoint,chooseRailPatch} from "./frontExterior";

function sample(){
 const w=201,h=281,p=new Uint8ClampedArray(w*h*4);
 const set=(x,y,rgb)=>p.set([...rgb,255],4*(y*w+x));
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const edge=Math.min(x,w-1-x,y,h-1-y);
  set(x,y,edge<6?[165,15,7]:edge<13?[220,160,45]:[248,224,174]);
 }
 // An original diamond on the left rail, with a golden outline and red core.
 const gem=[];
 for(let y=128;y<=152;y++)for(let x=1;x<=25;x++){
  const d=Math.abs(x-13)+Math.abs(y-140);
  if(d<=12){set(x,y,d>=9?[242,185,55]:[175,12,28]);gem.push([x,y]);}
 }
 return {w,h,p,gem};
}
it("keeps every original diamond pixel in the same location and shape",()=>{
 const {w,h,p,gem}=sample(),a=exteriorAlpha(p,w,h);
 for(const [x,y] of gem)expect(a[4*(y*w+x)+3]).toBe(0);
 expect(a[4*(140*w+100)+3]).toBe(0);
});
it("extends an undecorated original gold rail to the trim without moving existing gold",()=>{
 const {w,h,p}=sample(),a=exteriorAlpha(p,w,h);
 const at=(x,y)=>Array.from(a.slice(4*(y*w+x),4*(y*w+x)+4));
 for(const [x,y] of [[0,70],[200,70],[100,0],[100,280]])expect(at(x,y)).toEqual([220,160,45,255]);
 expect(at(6,70)).toEqual([0,0,0,0]);
 expect(at(100,140)).toEqual([0,0,0,0]);
 expect(a.length).toBe(w*h*4);
});
it("selects a quiet metallic rail section and keeps the complete perimeter",()=>{
 const {w,h,p}=sample(),trace=traceOuterRail(p,w,h),patch=chooseRailPatch(p,w,h,3);
 expect(trace.length).toBe(2*(w+h-2));
 expect(perimeterPoint(0,w,h)).toEqual([0,0]);
 expect(perimeterPoint(w-1,w,h)).toEqual([w-1,0]);
 expect(patch.start+patch.length<128||patch.start>152).toBe(true);
});
it("uses each original master and shares the class master with subclasses",()=>{
 expect(frontMaskSource("subclass")).toEqual(frontMaskSource("class"));
 expect(frontMaskSource("monster").src).toBe("/card-art/front-master-v17.webp");
 expect(frontMaskSource("spell").legacy).toBe(false);
 expect(frontMaskSource("feat").src).toBe("/card-art/master-talento-5x7.png");
});
