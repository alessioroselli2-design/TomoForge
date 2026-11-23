import {raceCardView,raceLineagesForCard} from "./raceCardView";
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
 it("cleans manual citations only in the display text, retaining Duergar and source data",()=>{
  const source="Nano delle Colline · Nano delle Montagne · Nano Grigio (Duergar, SCAG 2015)";
  const card=Object.freeze({type:"race",name:"Nano",
   attributes:Object.freeze({sottorazze:source})});
  expect(raceCardView(card).lineages).toBe(
   "Nano delle Colline · Nano delle Montagne · Nano Grigio (Duergar)"
  );
  expect(card.attributes.sottorazze).toBe(source);
  expect(raceLineagesForCard("Duergar (SCAG 2015)")).toBe("Duergar");
  expect(raceLineagesForCard("Nano Grigio (Duergar, SCAG 2015)")).toBe("Nano Grigio (Duergar)");
  expect(raceLineagesForCard("Elfo (Mordenkainen)")).toBe("Elfo (Mordenkainen)");
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
