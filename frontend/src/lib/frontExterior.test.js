import {exteriorAlpha,frontMaskSource,framePalette,patinaPixel} from "./frontExterior";

it("continues the original gold palette only outside the frame, preserving the gold and red art",()=>{
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
 const i=4*(70*w+1);expect(a[i]).toBeGreaterThan(a[i+1]);expect(a[i+1]).toBeGreaterThan(a[i+2]);
});
it("samples metallic colours, rejecting lava and ruby",()=>{
 const p=new Uint8ClampedArray([200,20,10,255,151,101,38,255,190,135,52,255,240,195,60,255]);
 const palette=framePalette(p,[0,4,8,12]);
 for(const value of Object.values(palette))expect([[151,101,38],[190,135,52],[240,195,60]]).toContainEqual(value);
});
it("uses subtle two-dimensional texture without an extrapolated row or column",()=>{
 const palette={shadow:[100,58,22],mid:[157,102,45],light:[192,139,67]};
 const at=(x,y)=>patinaPixel(palette,x,y,1020,1428,10);
 expect(at(12,800)).toEqual(at(12,800));
 expect(at(12,800)).not.toEqual(at(15,807));
 expect(at(12,800)[0]).toBeGreaterThan(at(12,800)[1]);
 expect(Math.abs(at(12,800)[0]-at(15,807)[0])).toBeLessThan(25);
});
it("uses each original master and shares the class master with subclasses",()=>{
 expect(frontMaskSource("subclass")).toEqual(frontMaskSource("class"));
 expect(frontMaskSource("monster").src).toBe("/card-art/front-master-v17.webp");
 expect(frontMaskSource("spell").legacy).toBe(false);
 expect(frontMaskSource("feat").src).toBe("/card-art/master-talento-5x7.png");
});
