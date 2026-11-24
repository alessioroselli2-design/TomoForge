// Read-only projection of the existing reference/card attributes.
export const CATEGORY_MASTERS = Object.freeze({
 feat:{master:"master-talento-5x7.png",symbol:"simbolo-talenti.png",subtitle:"Talento",section:"Benefici",footer:"Ripetibile e Note",fields:["Categoria","Prerequisito","Bonus Caratteristica"]},
 item:{master:"master-oggetto-magico-5x7.png",symbol:"simbolo-oggetti-magici.png",subtitle:"Oggetto Magico",section:"Proprietà",footer:"Maledizioni e Note",fields:["Tipo","Sintonia","Cariche"]},
 weapon:{master:"master-arma-5x7.png",symbol:"simbolo-armi-armature.png",subtitle:"Arma",section:"Proprietà e Maestria",footer:"Costo e Peso",fields:["Categoria","Tipo di Danno","Gittata"]},
 armor:{master:"master-armatura-5x7.png",symbol:"simbolo-armi-armature.png",subtitle:"Armatura",section:"Dettagli",footer:"Costo, Peso e Vestizione",fields:["Categoria","Requisiti","Furtività"]},
});
export const isCategoryMaster = type=>Object.prototype.hasOwnProperty.call(CATEGORY_MASTERS,type);
const clean=v=>typeof v==="string"||typeof v==="number"?String(v).trim():typeof v==="boolean"?(v?"Sì":"No"):"";
const text=v=>{
 const scalar=clean(v);if(scalar)return scalar;
 if(Array.isArray(v))return v.map(text).filter(Boolean).join(" · ");
 if(v&&typeof v==="object"){
  const name=clean(v.nome??v.name??v.titolo??v.title);
  const detail=text(v.descrizione??v.description??v.testo??v.text??v.valore??v.value??v.effetto??v.effect);
  if(name||detail)return [name,detail].filter(Boolean).join(": ");
  return Object.entries(v).map(([key,value])=>{const s=text(value);return s?key.replace(/_/g," ")+": "+s:"";}).filter(Boolean).join(" · ");
 }
 return "";
};
const firstRaw=(a,...keys)=>keys.map(k=>a[k]).find(v=>text(v)!=="");
const pick=(a,...keys)=>text(firstRaw(a,...keys));
const join=(...parts)=>parts.filter(Boolean).join(" · ");
const named=(name,value)=>value?name+": "+value:"";
const yesno=v=>{
 const s=text(v);
 if(/^(?:true|yes|s[iì])$/i.test(s))return "Sì";
 if(/^(?:false|no)$/i.test(s))return "No";
 return s;
};
const sentenceUnits=s=>String(s||"").trim().split(/\n+|(?<=[.!?;])\s+(?=[A-ZÀ-ÖØ-Þ0-9«“•-])| · /u).map(s=>s.trim()).filter(Boolean);
export const completeUnits=value=>{
 if(Array.isArray(value))return value.flatMap(completeUnits);
 if(value&&typeof value==="object")return [text(value)].filter(Boolean);
 return sentenceUnits(text(value));
};
const generic=(value,pattern)=>pattern.test(value)? "":value;
export function categoryCardView(card={}){
 const a=card.attributes||{}, config=CATEGORY_MASTERS[card.type];
 if(!config)return null;
 const description=text(card.description);
 const note=pick(a,"note","notes");
 const props=firstRaw(a,"proprieta","proprietà","properties");
 const costWeight=join(named("Costo",pick(a,"costo","cost")),named("Peso",pick(a,"peso","weight")));
 let badgeLabel="",badge="",values=[],body=[],footer="",subtitle=config.subtitle;
 switch(card.type){
 case "feat":{
  const prerequisite=pick(a,"prerequisito","prerequisiti","prerequisite");
  const rawLevel=pick(a,"livello_minimo","livello_richiesto","livello","min_level");
  const match=rawLevel.match(/^\d+$/)||prerequisite.match(/(?:livello\s+(\d+)|(\d+)[°º]?\s+livello)/i);
  badge=match?(match[1]||match[2]||match[0]):"";
  badgeLabel=badge?"LIV.":"";
  values=[pick(a,"categoria","feat_category"),prerequisite,pick(a,"bonus_caratteristiche","bonus_caratteristica","ability_score_increase")];
  body=completeUnits(firstRaw(a,"benefici","benefits")??description);
  const repeat=yesno(firstRaw(a,"ripetibile","repeatable"));
  footer=join(named("Ripetibile",repeat),note);
  break;
 }
 case "item":{
  badge=pick(a,"rarita","rarità","rarity");
  const type=pick(a,"tipo","tipo_oggetto","item_type")||generic(pick(a,"categoria"),/^oggetto(?: magico)?$/i);
  let attunement=yesno(firstRaw(a,"sintonia","richiede_sintonia","attunement"));
  if(/^richiede sintonia$/i.test(attunement))attunement="Sì";
  if(/^non richiede sintonia$/i.test(attunement))attunement="No";
  const requirement=pick(a,"requisito_sintonia","requisiti_sintonia","attunement_requirement");
  if(requirement&&attunement==="Sì")attunement+=" · "+requirement;
  const charges=pick(a,"cariche","charges");
  const recovery=pick(a,"recupero_cariche","charge_recovery");
  values=[type,attunement,join(charges,named("Recupero",recovery))];
  body=completeUnits(props??firstRaw(a,"effetto","effetti","effects")??description);
  if(props){const effects=completeUnits(firstRaw(a,"effetto","effetti","effects"));body=[...body,...effects.filter(s=>!body.includes(s))];}
  footer=join(named("Maledizioni",pick(a,"maledizioni","maledizione","curse")),note);
  break;
 }
 case "weapon":{
  const damage=pick(a,"danno","danni","formula_danno","damage");
  badge=(damage.match(/\b\d+d\d+(?:\s*[+-]\s*\d+)?\b/i)||[])[0]?.replace(/\s+/g,"")||(/^\d+$/.test(damage)?damage:"");
  badgeLabel=badge?"DANNI":"";
  const category=generic(pick(a,"categoria","weapon_category"),/^arma$/i);
  const kind=pick(a,"tipo_arma","tipo","weapon_type");
  values=[[...new Set([category,kind].filter(Boolean))].join(" · "),pick(a,"tipo_danno","damage_type"),pick(a,"gittata","portata","range")];
  body=completeUnits(props??description);
  const mastery=pick(a,"maestria","proprieta_maestria","mastery");
  if(mastery)body.push("Maestria: "+mastery);
  footer=costWeight;
  break;
 }
 case "armor":{
  const category=pick(a,"categoria","tipo","armor_category");
  const shield=/\bscud[oi]\b/i.test(category)||card.reference_type==="shield"||
   (Array.isArray(card.reference_snapshots)&&card.reference_snapshots.some(s=>s?.reference_type==="shield"));
  if(shield)subtitle="Scudo";
  const ac=pick(a,"classe_armatura","ca","armor_class");
  const formula=pick(a,"formula_ca","formula_classe_armatura","ac_formula")||ac;
  const base=(ac||formula).match(/^\s*([+]?\s*\d+)/)?.[1]?.replace(/\s+/g,"")||"";
  badge=shield&&base&&!base.startsWith("+")?"+"+base:base;
  badgeLabel=badge?"CA":"";
  const stealth=yesno(firstRaw(a,"svantaggio_furtivita","furtivita","stealth_disadvantage"));
  values=[shield?"Scudo":generic(category,/^armatura$/i),
   shield?pick(a,"competenza_scudi","competenze","requisiti","shield_proficiency"):pick(a,"forza_minima","forza","strength_requirement"),
   /^(s[iì]|svantaggio)$/i.test(stealth)?"Svantaggio":/^(no|false|nessuno)$/i.test(stealth)?"":stealth];
  body=[named("CA",formula),...completeUnits(firstRaw(a,"dettagli","proprieta","properties")??description),...completeUnits(note)].filter(Boolean);
  footer=join(costWeight,named("Vestizione",pick(a,"vestizione","tempo_vestizione","donning")));
  break;
 }
 default:break;
 }
 return {config,name:text(card.name)||"Senza nome",subtitle,badgeLabel,badge:badge|| (card.type==="feat"?"":"—"),values:values.map(v=>v||"—"),body:[...new Set(body.filter(Boolean))],footer:footer||"—"};
}
