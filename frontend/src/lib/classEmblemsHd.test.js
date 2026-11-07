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
 it("renders all 13 complete approved medals, aligned over one original ring",()=>{
   const css=readFileSync(resolve(__dirname,"../frontMasterV17.css"),"utf8");
   const exporter=readFileSync(resolve(__dirname,"./cardExport.js"),"utf8");
   const section=css.slice(css.lastIndexOf("/* Class medals:"));
   expect(section).toContain("left:3.47%!important;");
   expect(section).toContain("top:0.2%!important;");
   expect(section).toContain("width:24.85%!important;");
   expect(section).toContain("inset:8%");
   expect(section).toContain("background-size:100% 100%!important;");
   expect(section).toContain("-webkit-mask-image:none!important;");
   expect(section).toContain("clip-path:none!important;");
   expect(section).not.toContain("background-size:125% 125%");
   expect(exporter).toContain("const emblemSize=width*.2485;");
   expect(exporter).toContain("const emblemX=width*.0347;");
   expect(exporter).toContain("const emblemY=height*.002;");
   expect(exporter).toContain("ctx.drawImage(icon,emblemX,emblemY,emblemSize,emblemSize);");
   expect(exporter).not.toContain("{x:0,y:0,cell:512,zoom:1.25}");
 });
 it("does not affect existing class life dice or nonclass symbols",()=>{
   expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Drago"}}).sprite).toBe("drago-hd");
   const dieSource=readFileSync(resolve(__dirname,"./classHitDice.js"),"utf8");
   expect(dieSource).toContain("premium-v29.webp");
 });
});
