import {categoryCardView,completeUnits} from "./categoryCardView";
test("Maestro delle Armi: explicit fields, no invented level or bonuses",()=>{
 const v=categoryCardView({type:"feat",name:"Maestro delle Armi",attributes:{prerequisito:"",benefici:["Beneficio completo."]}});
 expect(v.badge).toBe("");expect(v.values).toEqual(["—","—","—"]);expect(v.body).toEqual(["Beneficio completo."]);
});
test("Bastone del Guardiano: retains rarity and attunement from attributes",()=>{
 const v=categoryCardView({type:"item",name:"Bastone del Guardiano",attributes:{rarita:"Molto raro",sintonia:"Richiede sintonia",tipo:"Bastone",cariche:0,recupero_cariche:"all'alba",proprieta:"Effetto completo."}});
 expect(v.badge).toBe("Molto raro");expect(v.values).toEqual(["Bastone","Sì","0 · Recupero: all'alba"]);
});
test("weapon: dice, type, range, complete properties and mastery",()=>{
 const v=categoryCardView({type:"weapon",name:"Spada",attributes:{danno:"1d8",categoria:"Da guerra",tipo_danno:"Tagliente",proprieta:["Versatile (1d10)","Accurata"],maestria:"Dati di prova",costo:"15 mo",peso:"1 kg"}});
 expect(v.badge).toBe("1d8");expect(v.values).toEqual(["Da guerra","Tagliente","—"]);expect(v.body).toEqual(["Versatile (1d10)","Accurata","Maestria: Dati di prova"]);
});
test("armor and shield keep base vs bonus, and unknown stealth blank",()=>{
 const a=categoryCardView({type:"armor",name:"Cotta di maglia",attributes:{classe_armatura:"16",forza_minima:"13",svantaggio_furtivita:"Sì",categoria:"Pesante"}});
 expect(a.badge).toBe("16");expect(a.values).toEqual(["Pesante","13","Svantaggio"]);
 const s=categoryCardView({type:"armor",name:"Scudo",attributes:{classe_armatura:"2",categoria:"Scudo"}});
 expect(s.badge).toBe("+2");expect(s.values).toEqual(["Scudo","—","—"]);
});
test("missing values and false are distinct; complete units are never character sliced",()=>{
 expect(categoryCardView({type:"feat",attributes:{ripetibile:false}}).footer).toBe("Ripetibile: No");
 expect(completeUnits("Prima frase. Seconda frase lunga.")).toEqual(["Prima frase.","Seconda frase lunga."]);
 expect(categoryCardView({type:"item",attributes:{sintonia:false}}).values[1]).toBe("No");
});
