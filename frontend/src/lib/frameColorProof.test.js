import {sampleBackGold,tintArmorMetal} from "./frameColorProof";
test("samples only the edges of the reverse",()=>{
 const w=100,h=140,p=new Uint8ClampedArray(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++)p.set(x<8||x>92?[181,115,49,255]:[250,210,40,255],4*(y*w+x));
 expect(sampleBackGold(p,w,h).v).toBe(181);
});
test("darkens metal without modifying protected parchment, gems or medallion pixels",()=>{
 const gold=[252,235,54,255],paper=[254,210,95,255],ruby=[220,15,25,255];
 const p=new Uint8ClampedArray([...gold,...paper,...ruby,...gold,...gold]);
 const before=p.slice(),protection=new Uint8ClampedArray([0,0,0,255,255,255,255,255,0,0,0,255,255,255,255,255,255,255,255,255]);
 const exterior=new Uint8ClampedArray(20);exterior[19]=255;
 const count=tintArmorMetal(p,before,protection,exterior,{h:32,s:.73,v:181});
 expect(count).toBe(2);
 expect(p[0]).toBeLessThan(200);
 expect(p[16]).toBeLessThan(200);
 expect(Array.from(p.slice(4,16))).toEqual(Array.from(before.slice(4,16)));
});
