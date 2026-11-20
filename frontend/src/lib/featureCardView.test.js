import { buildFeatureCardView, featureSentenceExcerpt } from "./featureCardView";

describe("privilege card — uses the actual record", () => {
 it("maps class, level, description and improvements without invented values", () => {
   const card = {
     type:"feature", name:"Forma Selvatica",
     description:"Puoi assumere una forma animale a te nota.",
     attributes:{classe:"Druido",livello:2,miglioramenti:"La trasformazione migliora ai livelli successivi."},
   };
   const view=buildFeatureCardView(card);
   expect(view.name).toBe("Forma Selvatica");
   expect(view.subtitle).toBe("Druido • Privilegio di Classe");
   expect(view.level).toBe("2");
   expect(view.description).toBe(card.description);
   expect(view.improvement).toBe(card.attributes.miglioramenti);
   expect(card.attributes.livello).toBe(2);
 });
 it("never invents a level or upgrades when absent", () => {
   const view=buildFeatureCardView({type:"feature",name:"Privilegio",attributes:{}});
   expect(view.level).toBe("");
   expect(view.improvement).toBe("");
   expect(view.subtitle).toBe("Privilegio di Classe");
 });
 it("does not cut a sentence halfway", () => {
   expect(featureSentenceExcerpt("Prima frase. Seconda frase molto lunga.",20))
     .toBe("Prima frase.");
 });
});
