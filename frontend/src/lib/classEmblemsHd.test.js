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
 it("fits every complete class medal into one identical measured box",()=>{
   const css=readFileSync(resolve(__dirname,"../frontMasterV17.css"),"utf8");
   const exporter=readFileSync(resolve(__dirname,"./cardExport.js"),"utf8");
   const section=css.slice(css.lastIndexOf("/* One canonical 512px Class medal"));
   expect(section).toContain("left:3.2%!important;");
   expect(section).toContain("top:0.65%!important;");
   expect(section).toContain("width:25%!important;");
   expect(section).toContain("background-size:100% 100%!important;");
   expect(section).toContain("inset:2.5%!important;");
   expect(section).toContain("mask-image:none!important;");
   expect(section).not.toContain(' .tf-v3-medallion[title="Guerriero"]');
   expect(section).not.toContain(' .tf-v3-medallion[title="Stregone"]');
   expect(section).not.toContain("background-size:158%");
   expect(exporter).toContain("const size=width*.25;");
   expect(exporter).toContain("const x=width*.032;");
   expect(exporter).toContain("const y=height*.0065;");
   expect(exporter).toContain("ctx.drawImage(icon,x,y,size,size);");
   expect(exporter).not.toContain("emblemZoom");
 });
 it("does not affect existing class life dice or nonclass symbols",()=>{
   expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Drago"}}).sprite).toBe("drago-hd");
   const dieSource=readFileSync(resolve(__dirname,"./classHitDice.js"),"utf8");
   expect(dieSource).toContain("premium-v29.webp");
 });
});
