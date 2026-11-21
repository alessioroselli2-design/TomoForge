import {buildFeatureCardView} from "./featureCardView";

describe("tutti i Privilegi: campi dinamici e descrizione solo effetto",()=>{
 it("Forma Selvatica IT: legge gli utilizzi strutturati e ricava azione + recupero dal testo",()=>{
  const description="Due usi per riposo breve o lungo. Si trasforma con un'azione in una bestia conosciuta: GS 1/4 al 2° livello, GS 1/2 al 4°, GS 1 all'8°; durata metà livello da druido in ore. Usa PF e caratteristiche fisiche della bestia.";
  const card={type:"feature",name:"Forma Selvatica",description,
   attributes:{classe_genitore:"Druido",livello:2,utilizzi_per_riposo:2}};
  const v=buildFeatureCardView(card);
  expect([v.activation,v.uses,v.recovery]).toEqual(["Azione","2","Riposo breve o lungo"]);
  expect(v.displayDescription).toMatch(/^Si trasforma in una bestia conosciuta/);
  expect(v.displayDescription).not.toMatch(/Due usi per riposo|con un'azione/);
  expect(v.description).toBe(description);
  expect(card.description).toBe(description);
 });
 it("versione ES: NON trasferisce il recupero o gli utilizzi dall'altra fonte",()=>{
  const description="Druido, 2° livello: come azione può trasformarsi magicamente in una bestia già vista, nel rispetto dei limiti del livello e del grado di sfida. Conserva le proprie caratteristiche mentali.";
  const v=buildFeatureCardView({type:"feature",name:"Forma Selvatica",description,
   attributes:{classe_genitore:"Druido",livello:2}});
  expect(v.activation).toBe("Azione");
  expect(v.uses).toBe("");
  expect(v.recovery).toBe("");
  expect(v.displayDescription).toMatch(/^Può trasformarsi magicamente/);
  expect(v.description).toBe(description);
 });
 it("rimuove una frase esclusivamente metadati mantenendo la trasformazione",()=>{
  const description="A partire dal 2° livello, un druido può usare la sua azione per assumere una forma animale. Può utilizzare questo privilegio due volte e recupera gli utilizzi spesi quando completa un riposo breve o lungo. Mantiene le caratteristiche mentali.";
  const v=buildFeatureCardView({type:"feature",description,attributes:{
   benefici:[description],utilizzi_per_riposo:2
  }});
  expect(v.activation).toBe("Azione");
  expect(v.uses).toBe("2");
  expect(v.recovery).toBe("Riposo breve o lungo");
  expect(v.displayDescription).toContain("un druido può assumere una forma animale");
  expect(v.displayDescription).toContain("Mantiene le caratteristiche mentali.");
  expect(v.displayDescription).not.toContain("recupera gli utilizzi");
 });
 it("Azione bonus: distingue la trasformazione del Circolo della Luna dall'azione normale",()=>{
  const description="Druido del Circolo della Luna, 2° livello: può assumere Forma Selvatica come azione bonus invece che come azione. Durante la trasformazione può spendere uno slot come azione bonus per recuperare PF.";
  const v=buildFeatureCardView({type:"feature",description,attributes:{}});
  expect(v.activation).toBe("Azione bonus");
  expect(v.displayDescription).toContain("invece che come azione");
  expect(v.uses).toBe("");
  expect(v.recovery).toBe("");
 });
 it("non scambia l'azione bonus per terminare Forma Selvatica con la sua attivazione",()=>{
  const description="Dal 2° livello il druido può usare un'azione per trasformarsi in una bestia. Può tornare alla forma normale come azione bonus.";
  const v=buildFeatureCardView({type:"feature",description,attributes:{}});
  expect(v.activation).toBe("Azione");
  expect(v.displayDescription).toContain("come azione bonus");
 });
 it("Ira della Tempesta: reazione, modificatore, riposo lungo",()=>{
  const v=buildFeatureCardView({type:"feature",name:"Ira della Tempesta",
   description:"Quando una creatura lo colpisce, usa reazione per costringerla a un TS Destrezza. Usi pari al modificatore di Saggezza per riposo lungo.",attributes:{}});
  expect(v.activation).toBe("Reazione");
  expect(v.uses).toBe("Mod. Saggezza");
  expect(v.recovery).toBe("Riposo lungo");
 });
 it("Carta Celeste: non confonde il riposo per ricreare un oggetto con quello che ricarica gli usi",()=>{
  const description="Puoi lanciare Dardo Tracciante senza usare slot un numero di volte pari al tuo bonus di competenza; recuperi questi utilizzi al termine di un riposo lungo. Puoi ricreare la carta durante un riposo breve o lungo.";
  const v=buildFeatureCardView({type:"feature",name:"Carta Celeste",description,
   attributes:{azione:"passiva"}});
  expect(v.activation).toBe("Passivo");
  expect(v.uses).toBe("Bonus competenza");
  expect(v.recovery).toBe("Riposo lungo");
  expect(v.displayDescription).toContain("Dardo Tracciante");
 });
 it("non prende il riposo che ripristina una CD come recupero degli utilizzi",()=>{
  const v=buildFeatureCardView({type:"feature",
   description:"Quando completa un riposo breve o lungo, la CD è ripristinata a 10.",
   attributes:{}});
  expect(v.recovery).toBe("");
 });
 it("non presenta un costo di due utilizzi come due utilizzi disponibili",()=>{
  const v=buildFeatureCardView({type:"feature",
   description:"Spendendo contemporaneamente due utilizzi di Forma Selvatica, puoi diventare un elementale.",attributes:{}});
  expect(v.uses).toBe("");
 });
 it("rispetta la precedenza dei campi affidabili e lascia il testo originale intatto",()=>{
  const description="Come azione può attivare il privilegio. Dopo un riposo lungo l'effetto termina.";
  const v=buildFeatureCardView({type:"feature",description,attributes:{
   tipo_attivazione:"Reazione",numero_utilizzi:3,recupero_utilizzi:"Riposo breve"
  }});
  expect([v.activation,v.uses,v.recovery]).toEqual(["Reazione","3","Riposo breve"]);
  expect(v.description).toBe(description);
 });
 it("senza metadati espliciti le caselle non inventano niente",()=>{
  const v=buildFeatureCardView({type:"feature",
   description:"Quando una creatura che vedi parla, ottieni un vantaggio alle prove di Intuizione.",attributes:{}});
  expect([v.activation,v.uses,v.recovery]).toEqual(["","",""]);
 });
});
