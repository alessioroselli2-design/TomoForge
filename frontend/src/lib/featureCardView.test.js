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
