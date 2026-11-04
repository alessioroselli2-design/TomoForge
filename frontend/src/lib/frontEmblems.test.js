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
  expect(getFrontEmblem({type:"class",name:"Guerriero"})).toMatchObject({src:"/card-art/class-emblems/CLS-05-guerriero.webp",cell:256,sprite:"classe-originale-256"});
 });
 it("uses the approved 52 race table and normalizes subrace labels",()=>{
  expect(getFrontEmblem({type:"race",name:"Eladrin"})).toMatchObject({sprite:"race",index:1});
  expect(getFrontEmblem({type:"race",name:"Hadozee"})).toMatchObject({sprite:"race",index:51});
  expect(getFrontEmblem({type:"race",name:"Gnomo delle Profondità"})).toMatchObject({sprite:"race",index:4});
 });
 it("keeps the user-approved Warrior crest (not an invented SVG)",()=>{
   expect(getFrontEmblem({type:"class",name:"Guerriero"})).toMatchObject({
     sprite:"classe-originale-256",src:"/card-art/class-emblems/CLS-05-guerriero.webp",cell:256
   });
   expect(getFrontEmblem({type:"class",name:"Druido"})).toMatchObject({sprite:"classe-originale-256",cell:256,src:"/card-art/class-emblems/CLS-04-druido.webp"});
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
 it("shows the original 256px approved CLS-05 Warrior emblem for Guerriero",()=>{
   const warrior=getFrontEmblem({type:"class",name:"Guerriero"});
   expect(warrior).toMatchObject({
     sprite:"classe-originale-256",
     src:"/card-art/class-emblems/CLS-05-guerriero.webp",
     backgroundSize:"100% 100%",
     width:256,height:256,cell:256,
   });
   expect(warrior.src).not.toContain(".svg");
 });
 it("does not disturb the approved red Dragon monster reference",()=>{
   expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Drago"}}))
     .toMatchObject({sprite:"drago-hd",src:"/emblemi/drago-originale-hd-v2.webp"});
 });
});

describe("Originale approvato per tutte le 13 classi",()=>{
 const all=["Barbaro","Bardo","Chierico","Druido","Guerriero","Monaco","Paladino","Ranger","Ladro","Stregone","Warlock","Mago","Artefice"];
 it.each(all.map((n,i)=>[n,String(i+1).padStart(2,"0")]))("%s remains CLS-%s in original resolution",(name,code)=>{
  const e=getFrontEmblem({type:"class",name});
  expect(e.src).toBe("/card-art/class-emblems/CLS-"+code+"-"+name.toLowerCase()+".webp");
  expect(e.cell).toBe(256);
  expect(e.backgroundSize).toBe("100% 100%");
 });
});