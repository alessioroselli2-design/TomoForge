import React,{act} from "react";
import {createRoot} from "react-dom/client";
import {CardFront} from "./TradingCard";
import {readFileSync} from "fs";
import {resolve} from "path";
global.IS_REACT_ACT_ENVIRONMENT=true;

const renderRace=async card=>{
 const host=document.createElement("div");document.body.appendChild(host);
 const root=createRoot(host);
 await act(async()=>root.render(<CardFront card={card} editorMode/>));
 return {host,close:async()=>{await act(async()=>root.unmount());host.remove()}};
};
describe("race-only 5x7 front",()=>{
 it("uses only the race master, original emblem, values and no QR",async()=>{
  const view=await renderRace({type:"race",name:"Elfo",attributes:{
   taglia:"Media",velocita:"9 m",scurovisione:"18 m",
   linguaggi:"Comune, Elfico",tratti:[{nome:"Sensi Acuti",descrizione:"Competenza in Percezione."}],
   sottorazze:"Elfo Alto"
  }});
  try{
   const card=view.host.querySelector('[data-front-layout="race-5x7-v1"]');
   expect(card.style.backgroundImage).toContain("master-razze-5x7.webp");
   expect(card.querySelector(".tf-race-emblem").getAttribute("src")).toBe("/emblemi/razze/rz-02-elfo.png");
   expect(card.querySelector(".tf-race-size").textContent).toContain("Media");
   expect(card.querySelector(".tf-race-title").textContent).toBe("Elfo");
   expect([...card.querySelectorAll("[data-race-field]")].map(x=>x.textContent)).toEqual(["9 m","18 m","Comune, Elfico"]);
   expect(card.querySelector(".tf-race-traits").textContent).toContain("Sensi Acuti.");
   expect(card.querySelector(".tf-race-lineages").textContent).toContain("Elfo Alto");
   expect(card.querySelector(".tf-race-illustration img")).toBeNull();
   expect(card.querySelector("[data-card-qr]")).toBeNull();
  }finally{await view.close()}
 });
 it("does not draw an invented icon or extra frame on unknown races",async()=>{
  const view=await renderRace({type:"race",name:"Razza non censita",attributes:{}});
  try{
   expect(view.host.querySelector(".tf-race-medallion img")).toBeNull();
   expect([...view.host.querySelectorAll("[data-race-field]")].map(x=>x.textContent)).toEqual(["—","—","—"]);
  }finally{await view.close()}
 });
 it("keeps React text nodes intact when layout fitting runs in the editor",async()=>{
  const view=await renderRace({type:"race",name:"",attributes:{tratti:[]}});
  try{
   const title=view.host.querySelector(".tf-race-title");
   const stat=view.host.querySelector('[data-race-field="speed"] .tf-race-stat-text');
   const titleNode=title.firstChild;
   const statNode=stat.firstChild;
   await act(async()=>{await Promise.resolve();await Promise.resolve()});
   expect(title.firstChild).toBe(titleNode);
   expect(stat.firstChild).toBe(statNode);
   expect(title.textContent).toBe("Senza nome");
   expect(stat.textContent).toBe("—");
  }finally{await view.close()}
 });
 it("switches from the editor's default spell to an empty race and updates it safely",async()=>{
  const host=document.createElement("div");document.body.appendChild(host);
  const root=createRoot(host);
  const Harness=()=>{
   const [card,setCard]=React.useState({type:"spell",name:"",attributes:{}});
   return <div>
    <button data-testid="select-race" onClick={()=>setCard({type:"race",name:"",attributes:{
     velocita:"",taglia:"",linguaggi:"",tratti:[]}})}>Razza</button>
    <button data-testid="select-elf" onClick={()=>setCard({type:"race",name:"Elfo",attributes:{
     velocita:"9 m",taglia:"Media",linguaggi:"Comune",tratti:[
      {nome:"Sensi Acuti",descrizione:"Competenza in Percezione."}]}})}>Elfo</button>
    <button data-testid="select-spell" onClick={()=>setCard({type:"spell",name:"",attributes:{}})}>Incantesimo</button>
    <CardFront card={card} editorMode/>
   </div>;
  };
  try{
   await act(async()=>root.render(<Harness/>));
   await act(async()=>{host.querySelector('[data-testid="select-race"]').click();await Promise.resolve()});
   expect(host.querySelector('[data-front-category="race"]')).not.toBeNull();
   expect(host.querySelector(".tf-race-title").textContent).toBe("Senza nome");
   await act(async()=>{host.querySelector('[data-testid="select-elf"]').click();await Promise.resolve()});
   expect(host.querySelector(".tf-race-title").textContent).toBe("Elfo");
   expect(host.querySelector('[data-race-field="speed"]').textContent).toBe("9 m");
   await act(async()=>{host.querySelector('[data-testid="select-spell"]').click();await Promise.resolve()});
   expect(host.querySelector('[data-front-category="race"]')).toBeNull();
  }finally{await act(async()=>root.unmount());host.remove()}
 });
 it("isolates race styles without important patches or extra raster art",()=>{
  const css=readFileSync(resolve(__dirname,"RaceCardFront.css"),"utf8");
  expect(css).not.toMatch(/!important|mask:|filter:|box-shadow:/);
  expect(css).toContain('[data-front-category="race"] .tf-race-emblem');
  expect(css).toContain('width:27.1%');
  expect(css).toContain('top:62%');
  expect(css).toMatch(/\.tf-race-subtitle\s*\{[^}]*top:-5px/);
 });
});
