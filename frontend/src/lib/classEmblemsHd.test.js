import { readFileSync } from "fs";
import { resolve } from "path";
import { getFrontEmblem } from "./frontEmblems";

describe("Class master with original gold well and only one dynamic inner motif",()=>{
 const names="barbaro bardo chierico druido guerriero monaco paladino ranger ladro stregone warlock mago artefice".split(" ");
 it.each(names)("%s uses original HD asset without a separate gold ring overlay",name=>{
   const emblem=getFrontEmblem({type:"class",name});
   expect(emblem.sprite).toBe("class-inner-v1");
   expect(emblem.src).toBe(`/emblemi/classi-hd/${name}.webp`);
   expect(emblem.width).toBe(512);
   const original=readFileSync(resolve(__dirname,`../../public${emblem.src}`));
   expect(original.subarray(0,4).toString()).toBe("RIFF");
   expect(original.subarray(8,12).toString()).toBe("WEBP");
 });
 it("one fixed ring, one cropped center in CSS and in PNG/PDF export",()=>{
   const css=readFileSync(resolve(__dirname,"../frontMasterV17.css"),"utf8");
   const exporter=readFileSync(resolve(__dirname,"./cardExport.js"),"utf8");
   const layouts=readFileSync(resolve(__dirname,"./frontCategoryLayouts.js"),"utf8");
   const section=css.slice(css.lastIndexOf("/* EXACT user Class master"));
   expect(section).toContain("left:6.25%!important;top:3.97135%!important;");
   expect(section).toContain("width:18.16406%!important;");
   expect(section).toContain("background-size:169.5% 169.5%!important;");
   expect(section).toContain("mask-image:radial-gradient(");
   expect(section).not.toContain("tf-bardo-proof");
   expect(layouts).toContain("/card-art/class-master-user-reference-v1.webp");
   const master=readFileSync(resolve(__dirname,"../../public/card-art/class-master-user-reference-v1.webp"));
   expect(master.subarray(0,4).toString()).toBe("RIFF");
   expect(master.subarray(8,12).toString()).toBe("WEBP");
   expect(master.length).toBeGreaterThan(100000);
   expect(exporter).toContain('s.sprite==="class-inner-v1"');
   expect(exporter).toContain("pctx.drawImage(icon,105,105,302,302,0,0,size,size)");
   expect(exporter).toContain("const medalSize=width*(186/1024);");
   expect(exporter).toContain("const medalX=width*(64/1024);");
   expect(exporter).toContain("const medalY=height*(61/1536);");
   expect(exporter).toContain("ctx.drawImage(off,medalX,medalY,medalSize,medalSize)");
 });
 it("does not alter approved Monster medallion or Class dice",()=>{
   expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Drago"}}).sprite).toBe("drago-hd");
   expect(readFileSync(resolve(__dirname,"./classHitDice.js"),"utf8")).toContain("premium-v29.webp");
 });
});
