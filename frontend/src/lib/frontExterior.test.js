import {safeExteriorTrace,exteriorAlpha,frontMaskSource,traceOuterRail,perimeterPoint,sampleRailProfile,roundedTrimDistance,measureFrameRails,bottomRailPlan} from "./frontExterior";

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
it("extends a continuous rail to the trim without moving existing gold",()=>{
 const {w,h,p}=sample(),a=exteriorAlpha(p,w,h);
 const at=(x,y)=>Array.from(a.slice(4*(y*w+x),4*(y*w+x)+4));
 for(const [x,y] of [[0,70],[200,70],[100,0],[100,280]])expect(at(x,y)).toEqual([220,160,45,255]);
 expect(at(0,70)).toEqual(at(0,100));
 expect(at(3,70)).toEqual([44,17,6,255]);
 expect(at(6,70)).toEqual([0,0,0,0]);
 expect(at(100,140)).toEqual([0,0,0,0]);
 expect(a.length).toBe(w*h*4);
});
it("samples a rail cross-section and keeps the complete perimeter",()=>{
 const {w,h,p}=sample(),trace=traceOuterRail(p,w,h),profile=sampleRailProfile(p,w,h);
 expect(trace.length).toBe(2*(w+h-2));
 expect(perimeterPoint(0,w,h)).toEqual([0,0]);
 expect(perimeterPoint(w-1,w,h)).toEqual([w-1,0]);
 expect(profile[0]).toEqual([220,160,45]);
 expect(roundedTrimDistance(0,0,w,h)).toBeLessThan(0);
 expect(roundedTrimDistance(0,140,w,h)).toBeCloseTo(0);
});
it("uses each original master and shares the class master with subclasses",()=>{
 expect(frontMaskSource("subclass")).toEqual(frontMaskSource("class"));
 expect(frontMaskSource("monster").src).toBe("/card-art/front-master-v17.webp");
 expect(frontMaskSource("spell").legacy).toBe(false);
 expect(frontMaskSource("feat").src).toBe("/card-art/master-talento-5x7.png");
});

it("measures the ornamental rails rather than the canvas and extends only a blank lower band",()=>{
 const w=200,h=280,p=new Uint8ClampedArray(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const rail=(y>=8&&y<=11)||(y>=263&&y<=266)||(y>=8&&y<=266&&((x>=6&&x<=9)||(x>=190&&x<=193)));
  const col=rail?[230,155,40]:y>=12&&y<263&&x>9&&x<190?[245,225,180]:[40,15,10];
  p.set([...col,255],4*(y*w+x));
 }
 const m=measureFrameRails(p,w,h);
 expect(m).toEqual({top:8,bottom:13,left:6,right:6});
 const plan=bottomRailPlan(p,w,h,m,{...m,bottom:5});
 expect(plan.delta).toBe(8);
 expect(plan.y+plan.band).toBeLessThan(263);
 expect(bottomRailPlan(p,w,h,m,m)).toBeNull();
});

it("does not paint the matte over a pale highlight or the adjoining carved outline",()=>{
 const {w,h,p}=sample(),artwork=p.slice();
 const set=(x,y,col)=>artwork.set([...col,255],4*(y*w+x));
 // The low-resolution reference misses a narrow protruding restored highlight.
 set(3,100,[251,225,207]);set(4,101,[67,39,20]);
 const a=exteriorAlpha(p,w,h,artwork);
 expect(a[4*(100*w+3)+3]).toBe(0);
 expect(a[4*(101*w+4)+3]).toBe(0);
 expect(a[4*(70*w)+3]).toBe(255);
 expect(safeExteriorTrace(artwork,w,h).length).toBe(2*(w+h-2));
});
