import { addPressCardPages } from "./pressExport";
import { renderCardCanvas, renderCardBackCanvas } from "./cardExport";
jest.mock("./cardExport",()=>({renderCardCanvas:jest.fn(),renderCardBackCanvas:jest.fn()}));
it("produces full-size upright faces and extends bleed outside trim",async()=>{
 const events=[],ctx={},drawImage=jest.fn();
 const spy=jest.spyOn(document,"createElement").mockImplementation(()=>({
  getContext:()=>({drawImage}),toDataURL:()=>"bleed"
 }));
 try{
 const pdf={internal:{getCurrentPageInfo:()=>({pageContext:ctx}),scaleFactor:72/25.4},
  addPage:()=>events.push("page"),addImage:(data,kind,...bounds)=>events.push([data,...bounds])};
 renderCardCanvas.mockImplementation(async(el,card)=>({width:1020,height:1428,toDataURL:()=>"front-"+card.id}));
 renderCardBackCanvas.mockImplementation(async(card)=>({width:1020,height:1428,toDataURL:()=>"back-"+card.id}));
 await addPressCardPages(pdf,{}, {id:"1"});
 await addPressCardPages(pdf,{}, {id:"2"},{first:false});
 expect(events.filter(x=>x==="page"||x[0]!=="bleed")).toEqual([["front-1",3,3,63.5,88.9],"page",["back-1",3,3,63.5,88.9],"page",["front-2",3,3,63.5,88.9],"page",["back-2",3,3,63.5,88.9]]);
 expect(events.filter(x=>x[0]==="bleed")).toHaveLength(4);
 expect(drawImage).toHaveBeenCalledTimes(36);
 }finally{spy.mockRestore();}
});
