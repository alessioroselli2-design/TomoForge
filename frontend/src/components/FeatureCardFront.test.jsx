import React,{act} from "react";
import {createRoot} from "react-dom/client";
import {CardFront} from "./TradingCard";
global.IS_REACT_ACT_ENVIRONMENT=true;
jest.mock("@/lib/api",()=>({artworkUrl:path=>"https://cdn.example.com/"+path}));
const mount=async card=>{
 const node=document.createElement("div");document.body.appendChild(node);
 const root=createRoot(node);await act(async()=>root.render(<CardFront card={card} editorMode/>));
 return {node,unmount:async()=>{await act(async()=>root.unmount());node.remove()}};
};
describe("class feature: immutable print master and dynamic values",()=>{
 it("renders only three values above a centered description, and never adds a QR or duplicate icons",async()=>{
  const view=await mount({type:"feature",name:"Forma Selvatica",description:"Puoi trasformarti in una bestia.",
   attributes:{classe:"Druido",livello:2,tipo_attivazione:"Azione",utilizzi_per_riposo:2,
    recupero:"Riposo breve o lungo",progressione:"Al livello 4, GS 1/2."}});
  try {
   expect(view.node.querySelector('[data-front-layout="feature-5x7-v5"]')).not.toBeNull();
   const values=[...view.node.querySelectorAll("[data-feature-field]")];
   expect(values).toHaveLength(3);
   expect(values.map(x=>x.textContent)).toEqual(["Azione","2","Riposo breve o lungo"]);
   expect(view.node.querySelector(".tf-feature-progression").textContent).toContain("GS 1/2");
   expect(view.node.querySelector(".tf-feature-description").textContent).toContain("trasformarti");
   expect(view.node.querySelector(".tf-feature-artwork img")).toBeNull();
   expect(view.node.querySelectorAll("[data-card-qr]")).toHaveLength(0);
   expect(view.node.querySelectorAll(".tf-feature-stat-value img")).toHaveLength(0);
   expect(view.node.querySelector(".tf-feature-original-emblem").getAttribute("src"))
     .toBe("/emblemi/privilegi/simbolo-privilegi-alta-risoluzione.png");
  } finally {await view.unmount()}
 });
 it("leaves empty progression and displays em dashes for missing stats",async()=>{
  const view=await mount({type:"feature",name:"Tratto",description:"Beneficio.",attributes:{}});
  try {
   expect([...view.node.querySelectorAll("[data-feature-field]")].map(x=>x.textContent))
    .toEqual(["—","—","—"]);
   expect(view.node.querySelector(".tf-feature-progression").textContent).toBe("");
  }finally{await view.unmount()}
 });
 it("allows the user's image in the master illustration well",async()=>{
  const view=await mount({type:"feature",name:"Tratto",attributes:{},artwork_path:"users/me/selected.png"});
  try {expect(view.node.querySelector(".tf-feature-artwork img").getAttribute("src"))
    .toContain("selected.png");}finally{await view.unmount()}
 });
});
