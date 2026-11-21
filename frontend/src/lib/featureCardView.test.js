import {buildFeatureCardView,featureSentences} from "./featureCardView";
describe("privilege fields reflect actual TomoForge metadata",()=>{
 it("uses typed record attributes when present",()=>{
  const v=buildFeatureCardView({type:"feature",name:"Forma Selvatica",description:"Come azione, puoi trasformarti.",
   attributes:{classe_genitore:"Druido",livello:2,utilizzi_per_riposo:2,
    recupero_utilizzi:"Riposo breve o lungo",limiti_forma_selvatica:[
     {livello:2,gs_max:"1/4"},{livello:4,gs_max:"1/2"},{livello:8,gs_max:"1"}
    ]}});
  expect(v.subtitle).toBe("Druido • Privilegio di Classe");
  expect(v.level).toBe("2");
  expect(v.uses).toBe("2");
  expect(v.activation).toBe("Azione");
  expect(v.recovery).toBe("Riposo breve o lungo");
  expect(v.progression).toContain("8° livello: GS 1");
 });
 it("does not fabricate empty stats",()=>{
  const v=buildFeatureCardView({type:"feature",description:"Fornisce una competenza.",attributes:{}});
  expect(v.activation).toBe("");
  expect(v.uses).toBe("");
  expect(v.recovery).toBe("");
  expect(v.progression).toBe("");
 });
 it("keeps sentence boundaries for measured text",()=>{
  expect(featureSentences("Prima. Seconda completa.")).toEqual(["Prima.","Prima. Seconda completa."]);
 });
 it("reads parent from the reference payload when attributes lack classe",()=>{
  const v=buildFeatureCardView({parent_class:"Paladino",level:3,attributes:{}});
  expect(v.subtitle).toBe("Paladino • Privilegio di Classe");
  expect(v.level).toBe("3");
 });
});


describe("progressione non duplicata nella descrizione dei Privilegi",()=>{
 const wildShape="Si trasforma in una bestia conosciuta: GS 1/4 al 2° livello, GS 1/2 al 4°, GS 1 all'8°; durata metà livello da druido in ore. Usa PF e caratteristiche fisiche della bestia, preserva caratteristiche mentali e competenze.";
 const levels=[
  {livello:2,gs_max:"1/4"},
  {livello:4,gs_max:"1/2"},
  {livello:8,gs_max:"1"},
 ];
 it("Forma Selvatica IT: elimina solo i tre GS ripetuti, mantiene durata ed effetti",()=>{
  const card={type:"feature",name:"Forma Selvatica",description:wildShape,
   attributes:{classe_genitore:"Druido",livello:2,limiti_forma_selvatica:levels}};
  const view=buildFeatureCardView(card);
  expect(view.progression).toBe("2° livello: GS 1/4 · 4° livello: GS 1/2 · 8° livello: GS 1");
  expect(view.displayDescription).toBe(
   "Si trasforma in una bestia conosciuta; durata metà livello da druido in ore. Usa PF e caratteristiche fisiche della bestia, preserva caratteristiche mentali e competenze."
  );
  expect(view.description).toBe(wildShape);
  expect(card.description).toBe(wildShape);
 });
 it("senza Progressione il testo non perde informazioni di GS",()=>{
  const view=buildFeatureCardView({type:"feature",name:"Forma Selvatica",
   description:wildShape,attributes:{classe_genitore:"Druido",livello:2}});
  expect(view.progression).toBe("");
  expect(view.displayDescription).toContain("GS 1/4 al 2° livello");
  expect(view.displayDescription).toContain("GS 1 all'8°");
 });
 it("non elimina GS che non corrispondono ai valori della Progressione",()=>{
  const view=buildFeatureCardView({type:"feature",
   description:"Può trasformarsi: GS 1/2 al 2° livello; conserva i PF.",
   attributes:{limiti_forma_selvatica:levels}});
  expect(view.displayDescription).toContain("GS 1/2 al 2° livello");
  expect(view.displayDescription).toContain("conserva i PF");
 });
 it("la Forma Selvatica in spagnolo resta indipendente dal record italiano",()=>{
  const description="Druido, 2° livello: come azione può trasformarsi magicamente in una bestia già vista, nel rispetto dei limiti del livello e del grado di sfida.";
  const view=buildFeatureCardView({type:"feature",name:"Forma Selvatica",description,
   attributes:{classe_genitore:"Druido",livello:2}});
  expect(view.progression).toBe("");
  expect(view.displayDescription).toMatch(/Può trasformarsi magicamente/);
  expect(view.description).toBe(description);
 });
});
