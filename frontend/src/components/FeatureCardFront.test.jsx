import React, { act } from "react";
import {createRoot} from "react-dom/client";
import {CardFront} from "./TradingCard";
global.IS_REACT_ACT_ENVIRONMENT=true;
jest.mock("qrcode.react",()=>({QRCodeCanvas:()=>null}));
jest.mock("@/lib/api",()=>({artworkUrl:path=>"https://cdn.example.com/"+path}));
describe("approved feature master with three stat wells",()=>{
 const mount=async card=>{
  const el=document.createElement("div");document.body.appendChild(el);
  const root=createRoot(el);await act(async()=>root.render(<CardFront card={card} editorMode/>));
  return {el,close:async()=>{await act(async()=>root.unmount());el.remove();}};
 };
 it("has exactly three dynamic stat wells and one integrated progression band",async()=>{
  const v=await mount({type:"feature",name:"Forma Selvatica",description:"Un effetto.",
   attributes:{classe:"Druido",livello:"2",attivazione:"Azione",utilizzi:"2",
     recupero:"Riposo breve",progressione:"Più forme in seguito."}});
  try {
   expect(v.el.querySelector('[data-front-layout="feature-5x7-v3"]')).not.toBeNull();
   expect(v.el.querySelectorAll(".tf-feature-stat")).toHaveLength(3);
   expect([...v.el.querySelectorAll("[data-feature-field]")].map(x=>x.dataset.featureField))
      .toEqual(["activation","uses","recovery"]);
   expect(v.el.querySelector('[data-feature-field="activation"] strong').textContent).toBe("Azione");
   expect(v.el.querySelector('[data-feature-field="uses"] strong').textContent).toBe("2");
   expect(v.el.querySelector('[data-feature-field="recovery"] strong').textContent).toBe("Riposo breve");
   expect(v.el.querySelector('[data-testid="feature-progression"]').textContent).toContain("Più forme");
   expect(v.el.querySelector(".tf-feature-footer")).toBeNull();
   expect(v.el.querySelector(".tf-feature-artwork img")).toBeNull();
   expect(v.el.querySelector(".tf-feature-original-emblem").getAttribute("src"))
     .toBe("/emblemi/privilegi-originale-v2.webp");
  } finally {await v.close();}
 });
 it("keeps all fields unfilled when absent but prints the three icons",async()=>{
  const v=await mount({type:"feature",name:"Tratto",attributes:{}});
  try {
   expect(v.el.querySelectorAll(".tf-feature-stat-body img")).toHaveLength(3);
   expect(v.el.querySelectorAll(".tf-feature-stat-body strong")).toHaveLength(0);
   expect(v.el.querySelector(".tf-feature-progression").textContent).toBe("");
   expect(v.el.querySelector(".tf-feature-level")).toBeNull();
  } finally {await v.close();}
 });
 it("uses the user's own illustration when provided",async()=>{
  const v=await mount({type:"feature",name:"Tratto",artwork_path:"images/example.jpg",attributes:{}});
  try {expect(v.el.querySelector(".tf-feature-artwork img").getAttribute("src"))
    .toContain("images/example.jpg");}finally{await v.close();}
 });
});
