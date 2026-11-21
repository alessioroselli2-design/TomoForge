import { getFrontEmblem } from "./frontEmblems";
import {readFileSync} from "fs";
import {resolve} from "path";
describe("approved TomoForge front medal rules",()=>{
 it("uses unique Beholder and Dragon monster medals",()=>{
  expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Aberrazione"}}).index).toBe(13);
  expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Drago"}})).toMatchObject({src:"/emblemi/drago-originale-hd-v2.webp", cell:160});
 });
 it("uses school-specific medals rather than a generic magic icon",()=>{
  expect(getFrontEmblem({type:"spell",attributes:{scuola:"Invocazione"}}).index).toBe(32);
  expect(getFrontEmblem({type:"spell",attributes:{scuola:"Necromanzia"}}).index).toBe(33);
 });
 it("uses all eight original transparent school PNGs, including English aliases",()=>{
   const schools=["abiurazione","ammaliamento","divinazione","evocazione",
     "illusione","invocazione","necromanzia","trasmutazione"];
   schools.forEach((school,i)=>{
     expect(getFrontEmblem({type:"spell",attributes:{scuola:school}})).toMatchObject({
       index:27+i,sprite:"school-original",cell:384,
       src:`/emblemi/scuole/scl-${String(i+1).padStart(2,"0")}-${school}.png`
     });
   });
   expect(getFrontEmblem({type:"spell",attributes:{school:"Evocation"}}).src)
     .toBe("/emblemi/scuole/scl-06-invocazione.png");
   expect(getFrontEmblem({type:"spell",attributes:{school:"Conjuration"}}).src)
     .toBe("/emblemi/scuole/scl-04-evocazione.png");
 });
 it("renders the full school PNG with the same Class geometry in the legacy preview and export",()=>{
   const component=readFileSync(resolve(__dirname,"../components/TradingCard.jsx"),"utf8");
   const css=readFileSync(resolve(__dirname,"../frontMasterV17.css"),"utf8");
   const exporter=readFileSync(resolve(__dirname,"cardExport.js"),"utf8");
   expect(component).toContain('symbol?.sprite==="school-original"');
   expect(css).toContain('[data-front-category="spell"] .tf-v3-medallion[data-emblem-sprite="school-original"]');
   expect(css).toContain('[data-front-category="spell"] .tf-school-original-emblem');
   expect(exporter).toContain('data.type==="spell"&&data.emblem.sprite==="school-original"');
 });
 it("distinguishes the new sapphire Privileges medal from the winged Cleric",()=>{
  expect(getFrontEmblem({type:"feature"})).toMatchObject({index:38,sprite:"feature-original",src:"/emblemi/privilegi-originale-v2.webp"});
  expect(getFrontEmblem({type:"class",name:"Chierico"}).index).toBe(2);
  expect(getFrontEmblem({type:"class",name:"Guerriero"})).toMatchObject({src:"/emblemi/classi/cls-05-guerriero.png",cell:320,sprite:"class-original"});
 });
 it("uses the approved 52 race table and normalizes subrace labels",()=>{
  expect(getFrontEmblem({type:"race",name:"Eladrin"})).toMatchObject({sprite:"race",index:1});
  expect(getFrontEmblem({type:"race",name:"Hadozee"})).toMatchObject({sprite:"race",index:51});
  expect(getFrontEmblem({type:"race",name:"Gnomo delle Profondità"})).toMatchObject({sprite:"race",index:4});
 });
 it("keeps the user-approved Warrior crest (not an invented SVG)",()=>{
   expect(getFrontEmblem({type:"class",name:"Guerriero"})).toMatchObject({
     sprite:"class-original",src:"/emblemi/classi/cls-05-guerriero.png",cell:320
   });
   expect(getFrontEmblem({type:"class",name:"Druido"}).sprite).toBe("class-original");
 });
 it("maps all 13 classes to their original, distinct PNG symbols",()=>{
   const classes=["Barbaro","Bardo","Chierico","Druido","Guerriero","Monaco",
     "Paladino","Ranger","Ladro","Stregone","Warlock","Mago","Artefice"];
   classes.forEach((name,index)=>{
     const expected=`/emblemi/classi/cls-${String(index+1).padStart(2,"0")}-${name.toLowerCase()}.png`;
     expect(getFrontEmblem({type:"class",name})).toMatchObject({
       index,sprite:"class-original",src:expected,
     });
   });
 });
 it("does not assign an incorrect medal when the type is unknown",()=>{
  expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Sconosciuto"}})).toBeNull();
 });
});
