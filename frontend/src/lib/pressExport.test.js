import { addPressCardPages } from "./pressExport";
import { renderCardCanvas, renderCardBackCanvas } from "./cardExport";
jest.mock("./cardExport",()=>({renderCardCanvas:jest.fn(),renderCardBackCanvas:jest.fn()}));

it("produces an upright front/back pair per card, in selected order",async()=>{
 const events=[], ctx={};
 const pdf={internal:{getCurrentPageInfo:()=>({pageContext:ctx}),scaleFactor:72/25.4},
  addPage:()=>events.push("page"),setFillColor:jest.fn(),rect:jest.fn(),
  addImage:(data)=>events.push(data)};
 renderCardCanvas.mockImplementation(async(el,card)=>({toDataURL:()=>"front-"+card.id}));
 renderCardBackCanvas.mockImplementation(async(card)=>({toDataURL:()=>"back-"+card.id}));
 await addPressCardPages(pdf,{}, {id:"1"});
 await addPressCardPages(pdf,{}, {id:"2"},{first:false});
 expect(events).toEqual(["front-1","page","back-1","page","front-2","page","back-2"]);
 expect(pdf.rect).toHaveBeenCalledTimes(4);
 expect(pdf.rect).toHaveBeenCalledWith(0,0,69.5,94.9,"F");
});
