import {classPrintNarrative} from "./classPrintNarrative";
describe("print descriptions use correct class-specific information",()=>{
 it("presents Fighter as Fighter, not the old vignette of a battle",()=>{
   const text=classPrintNarrative({
      name:"Guerriero",
      description:"Guerriero — D&D 5e, Manuale del Giocatore 2014. Dado Vita d10. Privilegi."
   },"Un'umana in una sferragliante corazza di piastre.");
   expect(text).toMatch(/Maestri del combattimento/);
   expect(text).not.toMatch(/Un'umana|Dado Vita d10/);
 });
 it("automatically changes the introduction for Druido and other classes",()=>{
   const c={description:"Druido — D&D 5e, Manuale del Giocatore 2014. Dado Vita d8."};
   expect(classPrintNarrative({...c,name:"Druido"})).toMatch(/forze naturali/);
   expect(classPrintNarrative({...c,name:"Guerriero"})).toMatch(/combattimento/);
 });
 it("never replaces user-authored or custom class description",()=>{
   expect(classPrintNarrative({name:"Guerriero",description:"Una descrizione personalizzata."}))
    .toBe("Una descrizione personalizzata.");
   expect(classPrintNarrative({name:"Classe originale",description:"D&D 5e, Manuale del Giocatore 2014. Dado Vita d8."}))
    .toBe("D&D 5e, Manuale del Giocatore 2014. Dado Vita d8.");
   expect(classPrintNarrative({}, "Descrizione storico-archivio."))
    .toBe("Descrizione storico-archivio.");
 });
});
