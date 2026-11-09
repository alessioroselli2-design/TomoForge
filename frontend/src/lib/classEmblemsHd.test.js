import { readFileSync } from "fs";
import { resolve } from "path";
import { getFrontEmblem } from "./frontEmblems";

describe("single engraved class medallion and automatic record mapping",()=>{
 const names="barbaro bardo chierico druido guerriero monaco paladino ranger ladro stregone warlock mago artefice".split(" ");
 it.each(names)("%s uses its own transparent 512px HD cutout in the shared medallion",name=>{
   const asset=getFrontEmblem({type:"class",name});
   expect(asset.sprite).toBe("class-approved-cutout");
   expect(asset.src).toBe(`/emblemi/classi-cutout/${name}.webp`);
   expect(asset.width).toBe(512);
   expect(asset.height).toBe(512);
   const bytes=readFileSync(resolve(__dirname,`../../public${asset.src}`));
   expect(bytes.subarray(0,4).toString()).toBe("RIFF");
   expect(bytes.subarray(8,12).toString()).toBe("WEBP");
   expect(bytes.length).toBeGreaterThan(8000);
 });
 it("has one fixed location, no extra gold rim, and the same canvas export",()=>{
   const css=readFileSync(resolve(__dirname,"../frontMasterV17.css"),"utf8");
   const exporter=readFileSync(resolve(__dirname,"./cardExport.js"),"utf8");
   const section=css.slice(css.lastIndexOf("/* Class emblem: one engraved circle"));
   expect(section).toContain("left:7.64706%!important;top:2.52101%!important;");
   expect(section).toContain("width:16.47059%!important;");
   expect(section).toContain("background-size:100% 100%!important;");
   expect(section).toContain("content:none!important;display:none!important;");
   expect(section).toContain("mask-image:none!important;");
   expect(section).not.toContain("[title=");
   expect(section).not.toContain("::before{\\n  content:\"\";");
   expect(section).not.toContain("background:radial-gradient(");
   expect(exporter).toContain('s.sprite==="class-approved-cutout"');
   expect(exporter).toContain("ctx.drawImage(icon,m.x-m.r,m.y-m.r,m.r*2,m.r*2);");
   expect(exporter).not.toContain("emblemZoom");
   expect(exporter).not.toContain("matteRadius");
 });
 it("does not modify hit dice or Monster symbols",()=>{
   expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Drago"}}).sprite).toBe("drago-hd");
   expect(readFileSync(resolve(__dirname,"./classHitDice.js"),"utf8")).toContain("premium-v29.webp");
 });
});
