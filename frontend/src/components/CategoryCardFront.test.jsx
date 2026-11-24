import React,{act} from "react";
import {createRoot} from "react-dom/client";
import {CategoryCardFront} from "./CategoryCardFront";
global.IS_REACT_ACT_ENVIRONMENT=true;
jest.mock("@/lib/api",()=>({artworkUrl:path=>"/mock/"+path}));
describe("dedicated category DOM",()=>{
 let mount,root;
 beforeEach(()=>{mount=document.createElement("div");document.body.appendChild(mount);root=createRoot(mount)});
 afterEach(()=>{act(()=>root.unmount());mount.remove()});
 test.each([["feat","talento","talenti"],["item","oggetto-magico","oggetti-magici"],["weapon","arma","armi-armature"],["armor","armatura","armi-armature"]])("%s has one raster and emblem, no QR",async(type,master,symbol)=>{
  await act(async()=>root.render(<CategoryCardFront card={{type,name:"Nome di prova",attributes:{}}}/>));
  const front=mount.querySelector("[data-category-master]");
  expect(front.style.backgroundImage).toContain("master-"+master+"-5x7.png");
  expect(front.querySelectorAll(".tf-category-emblem img")).toHaveLength(1);
  expect(front.querySelector(".tf-category-emblem img").getAttribute("src")).toBe("/emblemi/categorie/simbolo-"+symbol+".png");
  expect(front.querySelectorAll("[data-category-field]")).toHaveLength(3);
  expect(front.querySelector(".tf-category-artwork img")).toBeNull();
  expect(front.querySelector("[data-card-qr]")).toBeNull();
  expect(front.querySelector(".tf-v3-layout")).toBeNull();
 });
 test("record change keeps React-owned text",async()=>{
  await act(async()=>root.render(<CategoryCardFront card={{type:"feat",name:"Maestro delle Armi",attributes:{}}}/>));
  await act(async()=>root.render(<CategoryCardFront card={{type:"item",name:"Bastone del Guardiano con un titolo particolarmente lungo",artwork_path:"art.jpg",attributes:{rarita:"Molto raro"}}}/>));
  expect(mount.querySelector(".tf-category-name").textContent).toContain("Bastone del Guardiano");
  expect(mount.querySelector(".tf-category-artwork img").getAttribute("src")).toBe("/mock/art.jpg");
 });
});
