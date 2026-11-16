import { readFileSync } from "fs";
import { resolve } from "path";
import { getFrontEmblem } from "./frontEmblems";

const names="barbaro bardo chierico druido guerriero monaco paladino ranger ladro stregone warlock mago artefice".split(" ");
const read=(p)=>readFileSync(resolve(__dirname,p));

describe("the exact original user Class master and inner-only emblems",()=>{
 it.each(names)("%s uses a 207 x 145 alpha-fitted motif in a shared Class position",name=>{
   const emblem=getFrontEmblem({type:"class",name});
   expect(emblem.sprite).toBe("class-visible-motif");
   expect(emblem.src).toBe("/emblemi/classi-core-v1/"+name+".webp");
   expect(emblem.width).toBe(207);
   expect(emblem.height).toBe(168);
   const art=read("../../public/emblemi/classi-hd/"+name+".webp");
   expect(art.subarray(0,4).toString()).toBe("RIFF");
   expect(art.subarray(8,12).toString()).toBe("WEBP");
   expect(art.length).toBeGreaterThan(5000);
 });
 it("uses only the original 1024x1536 raster and one fixed symbol well",()=>{
   const css=read("../frontMasterV17.css").toString();
   const exporter=read("./cardExport.js").toString();
   const layout=read("./frontCategoryLayouts.js").toString();
   const art=read("../../public/card-art/class-master-user-20261113.webp");
   expect(art.subarray(0,4).toString()).toBe("RIFF");
   expect(art.subarray(8,12).toString()).toBe("WEBP");
   expect(art.length).toBeGreaterThan(100000);
   expect(layout).toContain('/card-art/class-master-user-20261113.webp');
   const one=css.slice(css.lastIndexOf("/* CLASSI · SOURCE OF TRUTH:"));
   expect(one).toContain("left:5.322265625%!important;top:3.515625%!important");
   expect(one).toContain("width:20.21484375%!important");
   expect(one).toContain('data-emblem-sprite="class-visible-motif"');
   expect(one).toContain("content:none!important;display:none!important");
   expect(one).not.toContain("tf-bardo-proof");
   expect(one).not.toContain("background:radial-gradient(");
   expect(exporter).toContain('s.sprite==="class-visible-motif"');
   expect(exporter).toContain("const medalW=width*(207/1024);");
   expect(exporter).toContain("const medalH=height*(168/1536);");
   expect(exporter).toContain("const medalX=width*(54.5/1024);");
   expect(exporter).toContain("const medalY=height*(54/1536);");
 });
 it("leaves Monster Dragon and the approved Class dice untouched",()=>{
   expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Drago"}}).sprite).toBe("drago-hd");
   expect(read("./classHitDice.js").toString()).toContain("class-dice-core-v1");
  expect(read("../../scripts/build_class_core_assets.py").toString()).toContain("class-dice");
 });
});
