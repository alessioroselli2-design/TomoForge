import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { CardFront } from "./TradingCard";
global.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock("qrcode.react", () => ({ QRCodeCanvas: () => null }));
jest.mock("@/lib/api", () => ({ artworkUrl: path => "https://cdn.example.com/" + path }));

describe("privilege cards use the dedicated approved master", () => {
 const mount = async card => {
   const el=document.createElement("div");document.body.appendChild(el);
   const root=createRoot(el);
   await act(async () => root.render(<CardFront card={card} editorMode/>));
   return {el,close:async()=>{await act(async()=>root.unmount());el.remove();}};
 };
 it("keeps an empty parchment image window, with the approved Privilegi emblem", async()=>{
   const v=await mount({type:"feature",name:"Forma Selvatica",
      description:"Puoi assumere una forma animale.",
      attributes:{classe:"Druido",livello:2,miglioramenti:"Migliora ai livelli superiori."}});
   try {
    expect(v.el.querySelector('[data-front-layout="feature-5x7-v1"]')).not.toBeNull();
    expect(v.el.querySelector(".tf-feature-artwork img")).toBeNull();
    expect(v.el.querySelector('[data-testid="front-emblem"]').dataset.emblemSprite).toBe("feature-original");
    expect(v.el.querySelector(".tf-feature-heading").textContent)
      .toContain("Druido • Privilegio di Classe");
    expect(v.el.querySelector(".tf-feature-level").textContent).toContain("2");
    expect(v.el.querySelector('[data-testid="feature-improvements"]').textContent)
      .toContain("Miglioramenti");
    expect(v.el.querySelector(".tf-feature-footer")).toBeNull();
    expect(v.el.querySelector(".tf-feature-original-emblem")?.getAttribute("src")).toBe("/emblemi/privilegi-originale-v2.webp");
    expect(v.el.querySelector(".tf-feature-art-hint")).not.toBeNull();
   } finally {await v.close();}
 });
 it("accepts a user-selected illustration and hides absent level/upgrades",async()=>{
   const v=await mount({type:"feature",name:"Capacità",artwork_path:"uploads/user-art.png",
     description:"Una descrizione reale.",attributes:{}});
   try {
    const img=v.el.querySelector(".tf-feature-artwork img");
    expect(img.getAttribute("src")).toContain("uploads/user-art.png");
    expect(v.el.querySelector(".tf-feature-level")).toBeNull();
    expect(v.el.querySelector(".tf-feature-improvement")).toBeNull();
    expect(v.el.querySelector(".tf-feature-art-hint")).toBeNull();
   } finally {await v.close();}
 });
});
