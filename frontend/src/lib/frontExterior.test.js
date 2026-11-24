import {exteriorAlpha,frontMaskSource,localRailColors,railPixel} from "./frontExterior";

it("continues the local gold relief only outside the frame, preserving red art and gold",()=>{
 const w=100,h=140,p=new Uint8ClampedArray(w*h*4);
 const pixel=(x,y,color)=>p.set([...color,255],4*(y*w+x));
 for(let y=0;y<h;y++)for(let x=0;x<w;x++)pixel(x,y,[165,15,7]);
 for(let x=3;x<=96;x++){pixel(x,4,[232,170,32]);pixel(x,134,[232,170,32]);}
 for(let y=4;y<=134;y++){pixel(3,y,[232,170,32]);pixel(96,y,[155,100,25]);}
 const a=exteriorAlpha(p,w,h),at=(x,y)=>a[4*(y*w+x)+3];
 expect(at(1,70)).toBe(255);expect(at(98,70)).toBe(255);
 expect(at(50,2)).toBe(255);expect(at(50,138)).toBe(255);
 expect(at(3,70)).toBe(0);expect(at(50,134)).toBe(0);
 expect(at(50,70)).toBe(0);expect(at(4,70)).toBe(0);
 expect(a[4*(70*w+1)]).toBeGreaterThan(a[4*(70*w+98)]);
});
it("uses each original master and shares the class master with subclasses",()=>{
 expect(frontMaskSource("subclass")).toEqual(frontMaskSource("class"));
 expect(frontMaskSource("monster").src).toBe("/card-art/front-master-v17.webp");
 expect(frontMaskSource("spell").legacy).toBe(false);
 expect(frontMaskSource("feat").src).toBe("/card-art/master-talento-5x7.png");
});
it("uses a warm bevel with a darker outer edge instead of a flat band",()=>{
 const c=[200,140,65];
 expect(railPixel(c,0,0,0)[0]).toBeGreaterThan(railPixel(c,1,0,0)[0]);
 expect(railPixel(c,.4,0,0)[0]).toBeGreaterThan(railPixel(c,.4,0,0)[1]);
});
