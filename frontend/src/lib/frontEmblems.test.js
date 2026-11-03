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
  expect(getFrontEmblem({type:"class",name:"Guerriero"})).toMatchObject({src:"/card-art/guerriero-reference-original-v36.webp",cell:168,sprite:"guerriero-approved"});
 });
 it("uses the approved 52 race table and normalizes subrace labels",()=>{
  expect(getFrontEmblem({type:"race",name:"Eladrin"})).toMatchObject({sprite:"race",index:1});
  expect(getFrontEmblem({type:"race",name:"Hadozee"})).toMatchObject({sprite:"race",index:51});
  expect(getFrontEmblem({type:"race",name:"Gnomo delle Profondità"})).toMatchObject({sprite:"race",index:4});
 });
 it("keeps the user-approved Warrior crest (not an invented SVG)",()=>{
   expect(getFrontEmblem({type:"class",name:"Guerriero"})).toMatchObject({
     sprite:"guerriero-approved",src:"/card-art/guerriero-reference-original-v36.webp",cell:168
   });
   expect(getFrontEmblem({type:"class",name:"Druido"}).sprite).toBe("core");
 });
 it("does not assign an incorrect medal when the type is unknown",()=>{
  expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Sconosciuto"}})).toBeNull();
 });
});

describe("All 13 class emblems reuse the same left medallion",()=>{
 const classNames=["Barbaro","Bardo","Chierico","Druido","Guerriero","Monaco","Paladino","Ranger","Ladro","Stregone","Warlock","Mago","Artefice"];
 it.each(classNames)("%s has its own valid class emblem",(name)=>{
   const emblem=getFrontEmblem({type:"class",name});
   expect(emblem).not.toBeNull();
   expect(emblem.label).toBe(name);
   expect(emblem.src).toMatch(/^\/(?:card-art|emblemi)\//);
 });
 it("shows the original 168px approved crossed-swords emblem for Guerriero",()=>{
   const warrior=getFrontEmblem({type:"class",name:"Guerriero"});
   expect(warrior).toMatchObject({
     sprite:"guerriero-approved",
     src:"/card-art/guerriero-reference-original-v36.webp",
     backgroundSize:"100% 100%",
     width:168,height:168,cell:168,
   });
   expect(warrior.src).not.toContain(".svg");
 });
 it("does not disturb the approved red Dragon monster reference",()=>{
   expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Drago"}}))
     .toMatchObject({sprite:"drago-hd",src:"/emblemi/drago-originale-hd-v2.webp"});
 });
});
