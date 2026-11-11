import { readFileSync } from "fs";
import { resolve } from "path";
import { getFrontEmblem } from "./frontEmblems";

describe("single Class master with one complete HD medallion",()=>{
 const names="barbaro bardo chierico druido guerriero monaco paladino ranger ladro stregone warlock mago artefice".split(" ");
 it.each(names)("%s uses the complete approved medal at a common scale",name=>{
   const emblem=getFrontEmblem({type:"class",name});
   expect(emblem.sprite).toBe("class-hd-single-ring");
   expect(emblem.src).toBe(`/emblemi/classi-hd/${name}.webp`);
   expect(emblem.width).toBe(512);
   expect(emblem.height).toBe(512);
   const original=readFileSync(resolve(__dirname,`../../public${emblem.src}`));
   expect(original.subarray(0,4).toString()).toBe("RIFF");
   expect(original.subarray(8,12).toString()).toBe("WEBP");
   expect(original.length).toBeGreaterThan(8000);
 });
 it("has one ring, identical placement for 13 classes and matching canvas export",()=>{
   const css=readFileSync(resolve(__dirname,"../frontMasterV17.css"),"utf8");
   const exporter=readFileSync(resolve(__dirname,"./cardExport.js"),"utf8");
   const layouts=readFileSync(resolve(__dirname,"./frontCategoryLayouts.js"),"utf8");
   const section=css.slice(css.lastIndexOf("/* A SINGLE complete approved"));
   expect(section).toContain("left:2.73585%!important;top:-0.33693%!important;");
   expect(section).toContain("width:24.5283%!important;");
   expect(section).toContain("background-size:100% 100%!important;");
   expect(section).toContain("content:none!important;display:none!important;");
   expect(section).toContain("mask-image:none!important;");
   expect(section).not.toContain("[title=");
   expect(section).not.toContain("background:radial-gradient(");
   expect(section).not.toContain("class-approved-cutout");
   expect(layouts).toContain('/card-art/class-master-single-ring-parchment-v2.webp');
   const clean=readFileSync(resolve(__dirname,"../../public/card-art/class-master-single-ring-parchment-v2.webp"));
   expect(clean.subarray(0,4).toString()).toBe("RIFF");
   expect(clean.subarray(8,12).toString()).toBe("WEBP");
   expect(clean.length).toBeGreaterThan(100000);
   expect(exporter).toContain('s.sprite==="class-hd-single-ring"');
   expect(exporter).toContain("const medalSize=width*(260/1060);");
   expect(exporter).toContain("const medalX=width*(29/1060);");
   expect(exporter).toContain("const medalY=height*(-5/1484);");
   expect(exporter).toContain("ctx.drawImage(icon,medalX,medalY,medalSize,medalSize);");
   expect(exporter).toContain('data.type==="class"?22.5');
   expect(exporter).toContain('data.type==="class"?9:7.7');
   expect(exporter).toContain('fontSize=10.1,lineHeight=11.82');
   expect(exporter).not.toContain("matteRadius");
 });
 it("keeps stat records, dice, and Monster medallions unchanged",()=>{
   expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Drago"}}).sprite).toBe("drago-hd");
   expect(readFileSync(resolve(__dirname,"./classHitDice.js"),"utf8")).toContain("premium-v29.webp");
 });
});
