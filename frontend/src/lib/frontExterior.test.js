import {exteriorAlpha,frontMaskSource,traceOuterRail,perimeterPoint} from "./frontExterior";
function sample(){
 const w=101,h=141,p=new Uint8ClampedArray(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const edge=Math.min(x,w-1-x,y,h-1-y);
  const rgb=edge<3?[165,15,7]:edge<7?[220,160,45]:[248,224,174];
  p.set([...rgb,255],4*(y*w+x));
 }
 return {w,h,p};
}
it("expands source gold to the outer trim and does not paint the central card",()=>{
 const {w,h,p}=sample(),a=exteriorAlpha(p,w,h);
 const at=(x,y)=>Array.from(a.slice(4*(y*w+x),4*(y*w+x)+4));
 expect(at(0,70)).toEqual([220,160,45,255]);
 expect(at(100,70)).toEqual([220,160,45,255]);
 expect(at(50,0)).toEqual([220,160,45,255]);
 expect(at(50,140)).toEqual([220,160,45,255]);
 expect(at(50,70)).toEqual([0,0,0,0]);
 expect(at(10,70)).toEqual([0,0,0,0]);
 expect(a.length).toBe(w*h*4);
});
it("traces the entire rectangular perimeter without changing dimensions",()=>{
 const {w,h,p}=sample(),trace=traceOuterRail(p,w,h);
 expect(trace.length).toBe(2*(w+h-2));
 expect(Array.from(trace).every(v=>v>=.82&&v<=1)).toBe(true);
 expect(perimeterPoint(0,w,h)).toEqual([0,0]);
 expect(perimeterPoint(w-1,w,h)).toEqual([w-1,0]);
});
it("uses each original master and shares the class master with subclasses",()=>{
 expect(frontMaskSource("subclass")).toEqual(frontMaskSource("class"));
 expect(frontMaskSource("monster").src).toBe("/card-art/front-master-v17.webp");
 expect(frontMaskSource("spell").legacy).toBe(false);
 expect(frontMaskSource("feat").src).toBe("/card-art/master-talento-5x7.png");
});
