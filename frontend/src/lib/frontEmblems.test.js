import { getFrontEmblem } from "./frontEmblems";
describe("approved TomoForge front medal rules",()=>{
 it("uses unique Beholder and Dragon monster medals",()=>{
  expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Aberrazione"}}).index).toBe(13);
  expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Drago"}})).toMatchObject({src:"/emblemi/drago-originale-hd-v2.webp", cell:160});
 });
 it("uses school-specific medals rather than a generic magic icon",()=>{
  expect(getFrontEmblem({type:"spell",attributes:{scuola:"Invocazione"}}).index).toBe(32);
  expect(getFrontEmblem({type:"spell",attributes:{scuola:"Necromanzia"}}).index).toBe(33);
 });
 it("distinguishes the new sapphire Privileges medal from the winged Cleric",()=>{
  expect(getFrontEmblem({type:"feature"}).index).toBe(38);
  expect(getFrontEmblem({type:"class",name:"Chierico"}).index).toBe(2);
  expect(getFrontEmblem({type:"class",name:"Guerriero"})).toMatchObject({src:"/emblemi/classi/cls-05-guerriero.png",cell:288,sprite:"class-png"});
 });
 it("uses the approved 52 race table and normalizes subrace labels",()=>{
  expect(getFrontEmblem({type:"race",name:"Eladrin"})).toMatchObject({sprite:"race",index:1});
  expect(getFrontEmblem({type:"race",name:"Hadozee"})).toMatchObject({sprite:"race",index:51});
  expect(getFrontEmblem({type:"race",name:"Gnomo delle Profondità"})).toMatchObject({sprite:"race",index:4});
 });
 it("uses the original transparent PNG Warrior crest rather than invented SVG",()=>{
   expect(getFrontEmblem({type:"class",name:"Guerriero"})).toMatchObject({
     sprite:"class-png",src:"/emblemi/classi/cls-05-guerriero.png",cell:288
   });
   expect(getFrontEmblem({type:"class",name:"Druido"}).src).toBe("/emblemi/classi/cls-04-druido.png");
 });
 it("maps all 13 original class PNGs and their parent-class variants",()=>{
   const names="Barbaro,Bardo,Chierico,Druido,Guerriero,Monaco,Paladino,Ranger,Ladro,Stregone,Warlock,Mago,Artefice".split(",");
   names.forEach((name,i)=>{
     const expected="/emblemi/classi/cls-"+String(i+1).padStart(2,"0")+"-"+name.toLowerCase()+".png";
     expect(getFrontEmblem({type:"class",name}).src).toBe(expected);
     expect(getFrontEmblem({type:"subclass",name:"Sottoclasse",attributes:{classe:name}}).src).toBe(expected);
     expect(getFrontEmblem({type:"character",name:"Eroe",attributes:{classe:name}}).src).toBe(expected);
   });
 });
 it("does not assign an incorrect medal when the type is unknown",()=>{
  expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Sconosciuto"}})).toBeNull();
 });
});
