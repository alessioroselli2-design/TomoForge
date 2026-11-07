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
 it("keeps the other twelve medals at approved size and corrects only Fighter",()=>{
   const css=readFileSync(resolve(__dirname,"../frontMasterV17.css"),"utf8");
   const exporter=readFileSync(resolve(__dirname,"./cardExport.js"),"utf8");
   expect(css).toContain("left:3.47%!important;top:1.1%!important;width:24.85%!important;");
   expect(css).toContain(' .tf-v3-medallion[title="Guerriero"]');
   expect(css).toContain(' .tf-v3-medallion[title="Fighter"]');
   expect(css).toContain("left:4.295%!important;top:0.7%!important;width:23.2%!important;");
   expect(exporter).toContain("fighter?0.232:0.2485");
   expect(exporter).toContain("fighter?0.04295:0.0347");
   expect(exporter).toContain("fighter?0.007:0.011");
 });
 it("does not affect existing class life dice or nonclass symbols",()=>{
   expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Drago"}}).sprite).toBe("drago-hd");
   const dieSource=readFileSync(resolve(__dirname,"./classHitDice.js"),"utf8");
   expect(dieSource).toContain("premium-v29.webp");
 });
});
