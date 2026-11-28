import { getFrontEmblem } from "./frontEmblems";
import {readFileSync} from "fs";
import {resolve} from "path";
describe("approved TomoForge front medal rules",()=>{
 it("uses unique Beholder and Dragon monster medals",()=>{
  expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Aberrazione"}}).index).toBe(13);
  expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Drago"}})).toMatchObject({src:"/emblemi/mostri/mst-05-drago.png", cell:640});
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
       index:27+i,sprite:"school-original",cell:640,
       src:`/emblemi/scuole-hd/scl-${String(i+1).padStart(2,"0")}-${school}-hd.png`
     });
   });
   expect(getFrontEmblem({type:"spell",attributes:{school:"Evocation"}}).src)
     .toBe("/emblemi/scuole-hd/scl-06-invocazione-hd.png");
   expect(getFrontEmblem({type:"spell",attributes:{school:"Conjuration"}}).src)
     .toBe("/emblemi/scuole-hd/scl-04-evocazione-hd.png");
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
  expect(getFrontEmblem({type:"feature"})).toMatchObject({index:38,sprite:"feature-original",src:"/emblemi/privilegi/simbolo-privilegi-alta-risoluzione.png"});
  expect(getFrontEmblem({type:"class",name:"Chierico"}).index).toBe(2);
  expect(getFrontEmblem({type:"class",name:"Guerriero"})).toMatchObject({src:"/emblemi/classi-hd/cls-05-guerriero-hd.png",cell:640,sprite:"class-original"});
 });
 it("keeps the race medal empty until a real race is selected",()=>{
   expect(getFrontEmblem({type:"race",name:"",attributes:{}})).toBeNull();
   expect(getFrontEmblem({type:"race",attributes:{}})).toBeNull();
   expect(getFrontEmblem({type:"race",name:"Razza inesistente"})).toBeNull();
   expect(getFrontEmblem({type:"race",name:"Umano"})).toMatchObject({
     sprite:"race-original",src:"/emblemi/razze/rz-01-umano.png"
   });
 });
 it("uses the approved 52 race table and normalizes subrace labels",()=>{
  expect(getFrontEmblem({type:"race",name:"Eladrin"})).toMatchObject({sprite:"race-original",index:1,src:"/emblemi/razze/rz-02-elfo.png"});
  expect(getFrontEmblem({type:"race",name:"Hadozee"})).toMatchObject({sprite:"race-original",index:51,src:"/emblemi/razze/rz-52-hadozee.png"});
  expect(getFrontEmblem({type:"race",name:"Gnomo delle Profondità"})).toMatchObject({sprite:"race-original",index:4,src:"/emblemi/razze/rz-05-gnomo.png"});
 });
 it("resolves original race PNGs and aliases for all requested spot checks",()=>{
   const files=[
     ["Umano","rz-01-umano.png"],["Elfo","rz-02-elfo.png"],
     ["Nano","rz-03-nano.png"],["Dragonide","rz-08-dragonide.png"],
     ["Goblin","rz-12-goblin.png"],["Tabaxi","rz-26-tabaxi.png"],
     ["Shifter","rz-33-morfico.png"],["Hadozee","rz-52-hadozee.png"],
     ["Simic Hybrid","rz-32-ibrido-simic.png"],["Hexblood","rz-50-sangue-strigo.png"],
     ["Drow","rz-02-elfo.png"],["Duergar","rz-03-nano.png"],
   ];
   files.forEach(([name,file])=>expect(getFrontEmblem({type:"race",name}))
     .toMatchObject({sprite:"race-original",src:"/emblemi/razze/"+file,cell:640}));
   expect(getFrontEmblem({type:"race",name:"Razza sconosciuta"})).toBeNull();
 });
 it("keeps the user-approved Warrior crest (not an invented SVG)",()=>{
   expect(getFrontEmblem({type:"class",name:"Guerriero"})).toMatchObject({
     sprite:"class-original",src:"/emblemi/classi-hd/cls-05-guerriero-hd.png",cell:640
   });
   expect(getFrontEmblem({type:"class",name:"Druido"}).sprite).toBe("class-original");
 });
 it("maps all 13 classes to their original, distinct PNG symbols",()=>{
   const classes=["Barbaro","Bardo","Chierico","Druido","Guerriero","Monaco",
     "Paladino","Ranger","Ladro","Stregone","Warlock","Mago","Artefice"];
   classes.forEach((name,index)=>{
     const expected=`/emblemi/classi-hd/cls-${String(index+1).padStart(2,"0")}-${name.toLowerCase()}-hd.png`;
     expect(getFrontEmblem({type:"class",name})).toMatchObject({
       index,sprite:"class-original",src:expected,
     });
   });
 });
 it("does not assign an incorrect medal when the type is unknown",()=>{
  expect(getFrontEmblem({type:"monster",attributes:{tipo_creatura:"Sconosciuto"}})).toBeNull();
 });
});

 it("maps all fourteen creature types and their English aliases to full 640px RGBA PNGs",()=>{
  const types=["aberrazione","bestia","celestiale","costrutto","drago","elementale","folletto","gigante","immondo","melma","mostruosita","non morto","pianta","umanoide"], aliases=["aberration","beast","celestial","construct","dragon","elemental","fey","giant","fiend","ooze","monstrosity","undead","plant","humanoid"];
  types.forEach((name,i)=>{
    const em=getFrontEmblem({type:"monster",attributes:{tipo_creatura:name}});
    expect(getFrontEmblem({type:"monster",attributes:{creature_type:aliases[i]}}).src).toBe(em.src);
    expect(em).toMatchObject({sprite:"monster-original",index:13+i,cell:640,width:640,height:640,col:0,row:0});
    expect(em.src).toBe("/emblemi/mostri/mst-"+String(i+1).padStart(2,"0")+"-"+name.replace(/ /g,"-")+".png");
    const png=readFileSync(resolve(__dirname,"../../public"+em.src));
    expect(png.subarray(0,8).toString("hex")).toBe("89504e470d0a1a0a");
    expect(png.readUInt32BE(16)).toBe(640);
    expect(png.readUInt32BE(20)).toBe(640);
    expect(png[25]).toBe(6); // truecolour with alpha
  });
  expect(getFrontEmblem({type:"monster",attributes:{}})).toBeNull();
 });
