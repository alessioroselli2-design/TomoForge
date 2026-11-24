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

test("real schema aliases: equipment and magic item",()=>{
 const w=categoryCardView({type:"weapon",attributes:{categoria:"Arma",categoria_arma:"guerra_mischia",danno:"1d8",tipo_danno:"tagliente",peso_kg:1.5,costo:"15 mo"}});
 expect(w.values).toEqual(["Da guerra · Mischia","tagliente","—"]);
 expect(w.footer).toBe("Costo: 15 mo · Peso: 1,5 kg");
 const a=categoryCardView({type:"armor",attributes:{categoria:"Armatura",categoria_armatura:"pesante",classe_armatura:"16",forza_minima:13,svantaggio_furtivita:true,peso_kg:27.5,costo:"75 mo",tempo_indossare:"10 minuti",tempo_togliere:"5 minuti"}});
 expect(a.values).toEqual(["Pesante","13","Svantaggio"]);expect(a.footer).toContain("Peso: 27,5 kg");expect(a.footer).toContain("Vestizione: 10 minuti");
 const shield=categoryCardView({type:"armor",attributes:{categoria_armatura:"scudo",classe_armatura:"+2 alla CA",svantaggio_furtivita:false}});
 expect(shield.badge).toBe("+2");expect(shield.values).toEqual(["Scudo","—","—"]);
 const i=categoryCardView({type:"item",attributes:{tipo:"Bastone",rarita:"raro",sintonia:"richiede sintonia con un druido",cariche_massime:10,recupero_cariche:"1d6+4 all’alba"}});
 expect(i.badge).toBe("Raro");expect(i.values).toEqual(["Bastone","Sì · con un druido","10 · Recupero: 1d6+4 all’alba"]);
 expect(categoryCardView({type:"feat",description:"Il suo punteggio di Forza o di Destrezza aumenta di 1, fino a un massimo di 20."}).values[2]).toBe("+1 Forza o Destrezza");
});
