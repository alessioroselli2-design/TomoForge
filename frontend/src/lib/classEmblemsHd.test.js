import { readFileSync } from "fs";
import { resolve } from "path";
import { getFrontEmblem } from "./frontEmblems";

const names="barbaro bardo chierico druido guerriero monaco paladino ranger ladro stregone warlock mago artefice".split(" ");
const read=(p)=>readFileSync(resolve(__dirname,p));

describe("the exact original user Class master and inner-only emblems",()=>{
 it.each(names)("%s uses the original colour artwork in exactly one Class rim",name=>{
   const emblem=getFrontEmblem({type:"class",name});
   expect(emblem.sprite).toBe("class-visible-motif");
   expect(emblem.src).toBe("/emblemi/classi-originali-da-prova/"+name+".png");
   expect(emblem.width).toBe(380);
   expect(emblem.height).toBe(380);
   const art=read("../../public/emblemi/classi-hd/"+name+".webp");
   expect(art.subarray(0,4).toString()).toBe("RIFF");
   expect(art.subarray(8,12).toString()).toBe("WEBP");
   expect(art.length).toBeGreaterThan(5000);
 });
 it("uses only the original 1024x1536 raster and one fixed symbol well",()=>{
   const css=read("../frontMasterV17.css").toString();
   const exporter=read("./cardExport.js").toString();
   const layout=read("./frontCategoryLayouts.js").toString();
   const art=read("../../public/card-art/references/approved-class-master-864x1210.webp");
   expect(art.subarray(0,4).toString()).toBe("RIFF");
   expect(art.subarray(8,12).toString()).toBe("WEBP");
   expect(art.length).toBeGreaterThan(100000);
   expect(layout).toContain('/card-art/references/approved-class-master-864x1210.webp');
   const one=css.slice(css.lastIndexOf("/* CLASSI · SOURCE OF TRUTH:"));
   expect(css).toContain("left:7%!important;top:4.25%!important");
   expect(css).toContain("width:17.4%!important");
   expect(one).toContain('data-emblem-sprite="class-visible-motif"');
   expect(one).toContain("content:none!important;display:none!important");
   expect(one).not.toContain("tf-bardo-proof");
   expect(one).not.toContain("background:radial-gradient(");
   expect(exporter).toContain("frontMasterAsset(data.type,data.emblem,data.dice)");
   expect(layout).not.toContain("class-composed-v5");
   expect(css).toContain(".tf-v3-medallion,");
   expect(css).toContain("left:75%!important;top:28.38%!important");
   expect(read("../../scripts/build_class_core_assets.py").toString()).toContain("build_embedded_class_masters");
 });
 it("leaves Monster Dragon and the approved Class dice untouched",()=>{
   expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Drago"}}).sprite).toBe("drago-hd");
   expect(read("./classHitDice.js").toString()).toContain("premium-v29.webp");
  expect(read("../../scripts/build_class_core_assets.py").toString()).toContain("MASTER_DIE_RECT = (751, 985, 218, 218)");
  expect(read("../../scripts/build_class_core_assets.py").toString()).toContain("class-dice");
 });
});
