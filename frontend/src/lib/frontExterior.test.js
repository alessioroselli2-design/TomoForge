import {exteriorAlpha,frontMaskSource,sampleAntiqueGold} from "./frontExterior";

it("extends the sampled gold only into the external surround while keeping the gold frame and red interior",()=>{
 const w=100,h=140,p=new Uint8ClampedArray(w*h*4);
 const pixel=(x,y,color)=>p.set([...color,255],4*(y*w+x));
 for(let y=0;y<h;y++)for(let x=0;x<w;x++)pixel(x,y,[165,15,7]);
 for(let x=3;x<=96;x++){pixel(x,4,[232,170,32]);pixel(x,134,[232,170,32]);}
 for(let y=4;y<=134;y++){pixel(3,y,[232,170,32]);pixel(96,y,[232,170,32]);}
 const a=exteriorAlpha(p,w,h),at=(x,y)=>a[4*(y*w+x)+3];
 expect(at(1,70)).toBe(255);expect(at(98,70)).toBe(255);
 expect(at(50,2)).toBe(255);expect(at(50,138)).toBe(255);
 expect(at(3,70)).toBe(0);expect(at(50,134)).toBe(0);
 expect(at(50,70)).toBe(0);expect(at(4,70)).toBe(0);
 expect(Array.from(a.slice(4*(70*w+1),4*(70*w+1)+4))).toEqual([232,170,32,255]);
});
it("uses the existing master for each category and the same Class master for subclasses",()=>{
 expect(frontMaskSource("subclass")).toEqual(frontMaskSource("class"));
 expect(frontMaskSource("monster").src).toBe("/card-art/front-master-v17.webp");
 expect(frontMaskSource("spell").legacy).toBe(false);
 expect(frontMaskSource("feat").src).toBe("/card-art/master-talento-5x7.png");
});

it("samples an actual antique-gold frame pixel and rejects red lava",()=>{
 const p=new Uint8ClampedArray([200,20,10,255,151,101,38,255,190,135,52,255,240,195,60,255]);
 expect(sampleAntiqueGold(p,[0,4,8,12])).toEqual([151,101,38]);
 expect(sampleAntiqueGold(p,[0])).toEqual([151,103,47]);
});
