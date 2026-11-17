import { fitClassDescription } from "./classDescriptionFit";
describe("static printed Class description",()=>{
 test("keeps the last complete sentence that fits the printable space",()=>{
   const source="Prima frase. Seconda frase più lunga. Terza frase molto più lunga e non stampabile.";
   const result=fitClassDescription(source,t=>t.length<=39);
   expect(result).toBe("Prima frase. Seconda frase più lunga.");
   expect(source.startsWith(result)).toBe(true);
   expect(result.endsWith(".")).toBe(true);
 });
 test("keeps full text when it fits, and never truncates a word",()=>{
   const source="Descrizione intera senza punto finale";
   expect(fitClassDescription(source,t=>t.length<70)).toBe(source);
 });
 test("truncates at the last comma or semicolon in an overlong first sentence",()=>{
   const text="Una descrizione iniziale molto estesa, con una subordinata molto lunga; e una parte successiva. Seconda frase.";
   expect(fitClassDescription(text,t=>t.length<=57)).toBe("Una descrizione iniziale molto estesa.");
 });
 test("never overflows by inserting a QR notice when no segment fits",()=>{
   expect(fitClassDescription("Una prima frase estremamente molto lunga. Altra frase.",t=>t.length<8)).toBe("");
 });
});
