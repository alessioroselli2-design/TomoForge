import { buildFeatureCardView, featureSentenceExcerpt } from "./featureCardView";
describe("feature card: live verified attributes",()=>{
 it("maps activation, uses, recovery, level and progression",()=>{
  const attrs={classe:"Druido",livello:2,tipo_attivazione:"Azione",
    utilizzi_disponibili:2,recupero_utilizzi:"Riposo breve",
    progressione:"Il GS massimo aumenta ai livelli superiori."};
  const card={type:"feature",name:"Forma Selvatica",attributes:attrs,
    description:"Puoi trasformarti in una bestia."};
  const v=buildFeatureCardView(card);
  expect([v.activation,v.uses,v.recovery]).toEqual(["Azione","2","Riposo breve"]);
  expect(v.progression).toBe(attrs.progressione);
  expect(v.improvement).toBe(v.progression);
  expect(v.level).toBe("2");
  expect(attrs.livello).toBe(2);
 });
 it("keeps absent fields and progression empty; never invents usage limits",()=>{
  const v=buildFeatureCardView({type:"feature",name:"Un tratto",description:"Un effetto passivo."});
  expect(v.activation).toBe("");
  expect(v.uses).toBe("");
  expect(v.recovery).toBe("");
  expect(v.progression).toBe("");
 });
 it("derives action only when explicitly stated in the description",()=>{
  expect(buildFeatureCardView({description:"Come azione, puoi farlo."}).activation).toBe("Azione");
  expect(buildFeatureCardView({description:"Usi la tua magia."}).activation).toBe("");
 });
 it("never cuts a printed sentence halfway",()=>{
  expect(featureSentenceExcerpt("Prima frase. Seconda frase molto lunga.",20)).toBe("Prima frase.");
 });
});
