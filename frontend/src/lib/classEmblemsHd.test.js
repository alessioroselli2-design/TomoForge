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
 it("uses one already engraved frame for all 13 symbols, removing duplicated rims",()=>{
   const css=readFileSync(resolve(__dirname,"../frontMasterV17.css"),"utf8");
   const exporter=readFileSync(resolve(__dirname,"./cardExport.js"),"utf8");
   const section=css.slice(css.lastIndexOf("/* Class emblems use the SINGLE medallion"));
   expect(section).toContain("left:7.64706%!important;");
   expect(section).toContain("top:2.52101%!important;");
   expect(section).toContain("width:16.47059%!important;");
   expect(section).toContain("border-radius:50%!important;");
   expect(section).toContain("background-size:170% 170%!important;");
   expect(section).toContain("mask-image:radial-gradient(");
   expect(section).toContain("content:none!important;");
   expect(section).not.toContain("width:24.85%!important;");
   expect(exporter).toContain("{x:0,y:0,cell:512,zoom:1.7}");
   expect(exporter).toContain(".37,.5);");
   expect(exporter).not.toContain("ctx.drawImage(icon,emblemX,emblemY");
 });
 it("does not affect existing class life dice or nonclass symbols",()=>{
   expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Drago"}}).sprite).toBe("drago-hd");
   const dieSource=readFileSync(resolve(__dirname,"./classHitDice.js"),"utf8");
   expect(dieSource).toContain("premium-v29.webp");
 });
});
