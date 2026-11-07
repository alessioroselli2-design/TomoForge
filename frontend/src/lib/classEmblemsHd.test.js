import { readFileSync } from "fs";
import { resolve } from "path";
import { getFrontEmblem } from "./frontEmblems";

describe("complete HD Class emblems from user-approved reference images",()=>{
 const names="barbaro bardo chierico druido guerriero monaco paladino ranger ladro stregone warlock mago artefice".split(" ");
 it.each(names)("%s has a full WEBP asset separate from the 44px atlas",(name)=>{
   const emblem=getFrontEmblem({type:"class",name});
   const asset=readFileSync(resolve(__dirname,`../../public${emblem.src}`));
   expect(asset.subarray(0,4).toString()).toBe("RIFF");
   expect(asset.subarray(8,12).toString()).toBe("WEBP");
   expect(asset.length).toBeGreaterThan(8000);
 });
 it("all 13 Class motifs fit the existing engraved Monster well, not a second medal",()=>{
   const css=readFileSync(resolve(__dirname,"../frontMasterV17.css"),"utf8");
   const exporter=readFileSync(resolve(__dirname,"./cardExport.js"),"utf8");
   const section=css.slice(css.lastIndexOf("/* Class symbols 2026-11-07:"));
   expect(section).toContain("left:7.64706%!important;");
   expect(section).toContain("top:2.52101%!important;");
   expect(section).toContain("width:16.47059%!important;");
   expect(section).toContain("overflow:hidden!important;");
   expect(section).toContain("background-size:125% 125%!important;");
   expect(section).toContain("mask-image:radial-gradient(");
   expect(section).not.toContain(' .tf-v3-medallion[title="Guerriero"]');
   expect(exporter).toContain("{x:0,y:0,cell:512,zoom:1.25}");
   expect(exporter).toContain(".335,.5);");
   expect(exporter).not.toContain("fighter?0.232:0.2485");
 });
 it("does not affect existing class life dice or nonclass symbols",()=>{
   expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Drago"}}).sprite).toBe("drago-hd");
   const dieSource=readFileSync(resolve(__dirname,"./classHitDice.js"),"utf8");
   expect(dieSource).toContain("premium-v29.webp");
 });
});
