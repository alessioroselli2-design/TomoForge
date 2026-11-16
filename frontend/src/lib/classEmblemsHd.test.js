import { readFileSync } from "fs";
import { resolve } from "path";
import { getFrontEmblem } from "./frontEmblems";

const names="barbaro bardo chierico druido guerriero monaco paladino ranger ladro stregone warlock mago artefice".split(" ");
const read=(p)=>readFileSync(resolve(__dirname,p));

describe("the exact original user Class master and inner-only emblems",()=>{
 it.each(names)("%s uses a 216px approved-format motif in a shared Class position",name=>{
   const emblem=getFrontEmblem({type:"class",name});
   expect(emblem.sprite).toBe("class-inner-on-original");
   expect(emblem.src).toBe("/emblemi/classi-inner/"+name+".webp");
   expect(emblem.width).toBe(216);
   expect(emblem.height).toBe(216);
   const art=read("../../public"+emblem.src);
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
   expect(one).toContain("left:4.8828125%!important;top:2.734375%!important");
   expect(one).toContain("width:21.09375%!important");
   expect(one).toContain('data-emblem-sprite="class-inner-on-original"');
   expect(one).toContain("content:none!important;display:none!important");
   expect(one).not.toContain("tf-bardo-proof");
   expect(one).not.toContain("background:radial-gradient(");
   expect(exporter).toContain('s.sprite==="class-inner-on-original"');
   expect(exporter).toContain("const medalSize=width*(216/1024);");
   expect(exporter).toContain("const medalX=width*(50/1024);");
   expect(exporter).toContain("const medalY=height*(42/1536);");
 });
 it("leaves Monster Dragon and the approved Class dice untouched",()=>{
   expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Drago"}}).sprite).toBe("drago-hd");
   expect(read("./classHitDice.js").toString()).toContain("premium-v29.webp");
 });
});
