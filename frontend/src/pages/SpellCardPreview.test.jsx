import {spellPreviewData} from "./SpellCardPreview";

describe("Incantesimo prototype (read-only, source-driven)",()=>{
 it("puts the school, not the caster class or level, under the title",()=>{
  const v=spellPreviewData({type:"spell",name:"Palla di Fuoco",
   attributes:{scuola:"Invocazione",classe:"Mago",livello:"3",
    tempo_lancio:"1 azione",gittata:"45 m",durata:"Istantanea",componenti:"V, S, M",
    tiro_salvezza:"Destrezza",esito_ts:"metà",danno:"8d6",
    area_effetto:"Sfera, raggio 6 m",tipo_danno:"Fuoco"}});
  expect(v.subtitle).toBe("Incantesimo di Invocazione");
  expect(v.level).toBe("3");
  expect(v.subtitle).not.toContain("Mago");
  expect(v.subtitle).not.toContain("livello");
  expect(v.details.map(x=>x.value)).toEqual(["1 azione","45 m","Istantanea","V, S, M"]);
  expect(v.tactics[0].value).toBe("TS Des · metà");
  expect(v.dice).toBe("8d6");
  expect(v.dieAsset).toBe("/card-art/spell-dice/d6-blank-v31.webp");
 });
 it("shows concentration without inventing a damage jewel",()=>{
  const v=spellPreviewData({type:"spell",name:"Benedizione",
   attributes:{scuola:"Ammaliamento",livello:"1",durata:"1 minuto",concentrazione:true}});
  expect(v.details[2].value).toBe("Conc. 1 minuto");
  expect(v.dice).toBe("");
  expect(v.dieAsset).toBe("");
 });
 it("distinguishes an explicitly negated save from a half-save",()=>{
  const v=spellPreviewData({type:"spell",name:"Blocca Persone",
   attributes:{scuola:"Ammaliamento",tiro_salvezza:"Saggezza",esito_ts:"nega"}});
  expect(v.tactics[0].value).toBe("TS Sag · nega");
 });
 it("does not fabricate combat mechanics for an incomplete record",()=>{
  const v=spellPreviewData({type:"spell",name:"Mancante"});
  expect(v.dice).toBe("");
  expect(v.tactics[0].value).toBe("—");
  expect(v.details.every(x=>x.value==="—")).toBe(true);
 });
});
