import {raceCardView} from "./raceCardView";
describe("race 5x7: real data only",()=>{
 it("reads the Italian race fields and preserves structured trait names",()=>{
  const view=raceCardView({
   type:"race",name:"Elfo",
   attributes:{
    taglia:"Media",velocita:"9 m",scurovisione:"18 m",
    linguaggi:["Comune","Elfico"],
    tratti:[{nome:"Retaggio Fatato",descrizione:"Vantaggio contro charme."}],
    sottorazze:["Elfo Alto","Elfo dei Boschi"]
   }
  });
  expect(view).toMatchObject({
   size:"Media",speed:"9 m",darkvision:"18 m",
   languages:"Comune · Elfico",lineages:"Elfo Alto · Elfo dei Boschi",
   traits:[{name:"Retaggio Fatato",description:"Vantaggio contro charme."}],
  });
 });
 it("reads explicit darkvision trait when there is no named darkvision field",()=>{
  expect(raceCardView({attributes:{
   tratti_razza:[{name:"Scurovisione",description:"18 metri."}]
  }}).darkvision).toBe("18 metri.");
 });
 it("does not invent size, speed, darkvision or languages",()=>{
  expect(raceCardView({type:"race",name:"Umano",attributes:{}})).toMatchObject({
   size:"—",speed:"—",darkvision:"—",languages:"—",lineages:""
  });
 });
 it("falls back to the full plain description when no trait array exists",()=>{
  const view=raceCardView({type:"race",name:"Genasi",description:"Testo attestato nell'archivio.",attributes:{tratti:[]}});
  expect(view.traits).toEqual([{name:"",description:"Testo attestato nell'archivio."}]);
 });
});
