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
const cap=s=>s?s[0].toUpperCase()+s.slice(1):"";
const metric=(value,unit)=>text(value)?text(value).replace(".",",")+" "+unit:"";
const weaponCategories={guerra_mischia:"Da guerra · Mischia",guerra_distanza:"Da guerra · Distanza",semplice_mischia:"Semplice · Mischia",semplice_distanza:"Semplice · Distanza"};
function explicitIncrease(description){
 const m=description.match(/punteggio (?:di|in) ((?:Forza|Destrezza|Costituzione|Intelligenza|Saggezza|Carisma)(?:(?:\s*,\s*|\s+o\s+(?:di\s+)?|\s+e\s+(?:di\s+)?)(?:Forza|Destrezza|Costituzione|Intelligenza|Saggezza|Carisma))*)\s+aumenta di\s+(\d+)/i);
 return m?"+"+m[2]+" "+m[1].replace(/\s+di\s+/gi," ").trim():"";
}
// Only discard metadata already shown elsewhere, never gameplay effects.
const keyText=s=>String(s||"").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[’']/g,"'").replace(/[.!?;:]+$/,"").replace(/\s+/g," ").trim();
const stripMeta=(units,metadata,extra=[])=>{
 const keys=new Set(extra.map(keyText));
 for(const [label,value] of metadata){
  if(value&&value!=="—"){
   keys.add(keyText(value));keys.add(keyText(label+": "+value));keys.add(keyText(label+" "+value));
  }
 }
 return units.flatMap(unit=>{
  const parts=unit.split(/;\s+|(?=\s+-\s+)/).map(s=>s.trim()).filter(Boolean);
  const kept=parts.filter(part=>!keys.has(keyText(part)));
  return kept.length===parts.length?[unit]:kept.length?[kept.join("; ")]:[];
 });
};
const armorModifier=(formula,badge)=>{
 if(!formula||!badge||!formula.startsWith(badge))return "";
 const remainder=formula.slice(badge.length).trim();
 if(!/\b(?:Des(?:trezza)?|Dex(?:terity)?)\b/i.test(remainder))return "";
 return "Modificatore alla CA: "+remainder.replace(/^\+\s*/,"+ ");
};
const clarifyWeaponProperty=unit=>unit.replace(/\bVersatile\s*\(\s*(\d+d\d+(?:\s*[+-]\s*\d+)?)\s*\)/gi,(_,dice)=>"Versatile: "+dice+" a due mani");
export function categoryCardView(card={}){
 const a=card.attributes||{}, config=CATEGORY_MASTERS[card.type];
 if(!config)return null;
 const description=text(card.description);
 const note=pick(a,"note","notes");
 const props=firstRaw(a,"proprieta","proprietà","properties");
 const costWeight=join(named("Costo",pick(a,"costo","cost")),named("Peso",pick(a,"peso","weight")||metric(a.peso_kg,"kg")));
 let badgeLabel="",badge="",values=[],body=[],footer="",subtitle=config.subtitle;
 switch(card.type){
 case "feat":{
  const prerequisite=pick(a,"prerequisito","prerequisiti","requisito","prerequisite");
  const rawLevel=pick(a,"livello_minimo","livello_richiesto","livello","min_level");
  const match=rawLevel.match(/^\d+$/)||prerequisite.match(/(?:livello\s+(\d+)|(\d+)[°º]?\s+livello)/i);
  badge=match?(match[1]||match[2]||match[0]):"";
  badgeLabel=badge?"LIV.":"";
  values=[pick(a,"categoria","feat_category"),prerequisite,pick(a,"aumento_caratteristica","bonus_caratteristiche","bonus_caratteristica","ability_score_increase")||explicitIncrease(description)];
  body=completeUnits(firstRaw(a,"benefici","benefits")??description);
  if(values[2])body=body.map(unit=>{
   const increase=explicitIncrease(unit);
   if(!increase||keyText(increase)!==keyText(values[2]))return unit;
   if(/^\s*(?:[-•]\s*)?(?:il suo |il )?punteggio/i.test(unit)){
    const max=unit.match(/fino a un massimo di (\d+)\s*[.!]?$/i);
    if(max)return "Limite dell'aumento: "+max[1]+".";
    if(/aumenta di \d+\s*[.!]?$/i.test(unit))return "";
   }
   return unit;
  }).filter(Boolean);
  body=stripMeta(body,[["Prerequisito",prerequisite],["Categoria",values[0]],["Bonus caratteristica",values[2]],["Livello",badge]]);
  const repeat=yesno(firstRaw(a,"ripetibile","repeatable"));
  footer=join(named("Ripetibile",repeat),note);
  break;
 }
 case "item":{
  badge=cap(pick(a,"rarita","rarità","rarity"));
  const type=pick(a,"tipo","tipo_oggetto","item_type")||generic(pick(a,"categoria"),/^oggetto(?: magico)?$/i);
  let attunement=yesno(firstRaw(a,"sintonia","richiede_sintonia","requires_attunement","attunement"));
  if(/^richiede sintonia$/i.test(attunement))attunement="Sì";
  if(/^non richiede sintonia$/i.test(attunement))attunement="No";
  else if(/^richiede sintonia\s+/i.test(attunement))attunement=attunement.replace(/^richiede sintonia\s+/i,"Sì · ");
  const requirement=pick(a,"prerequisito_sintonia","requisito_sintonia","requisiti_sintonia","attunement_requirement");
  if(requirement&&attunement==="Sì")attunement+=" · "+requirement;
  else if(attunement&&!/^(?:Sì|No|—)/i.test(attunement)&&!/^non /i.test(attunement))attunement="Sì · "+attunement;
  const charges=pick(a,"cariche_massime","max_cariche","cariche","charges");
  const recovery=pick(a,"recupero_cariche","ricarica","recupero","recupero_cariche_formula","charge_recovery");
  values=[type,attunement,join(charges,named("Recupero",recovery))];
  body=completeUnits(props??firstRaw(a,"effetto","effetti","effects")??description);
  if(props){const effects=completeUnits(firstRaw(a,"effetto","effetti","effects")??description);body=[...body,...effects.filter(s=>!body.includes(s))];}
  footer=join(named("Maledizioni",pick(a,"maledizioni","maledizione","curse")||yesno(firstRaw(a,"maledetto"))),note);
  body=stripMeta(body,[["Rarità",badge],["Tipo",type],["Sintonia",attunement],["Cariche",charges],["Recupero",recovery]],[charges?charges+" cariche":"",recovery?"ricarica "+recovery:""]);
  break;
 }
 case "weapon":{
  const damage=pick(a,"danno","danni","formula_danno","damage");
  badge=(damage.match(/\b\d+d\d+(?:\s*[+-]\s*\d+)?\b/i)||[])[0]?.replace(/\s+/g,"")||(/^\d+$/.test(damage)?damage:"");
  badgeLabel=badge?"DANNI":"";
  const rawCategory=pick(a,"categoria_arma");
  const category=weaponCategories[rawCategory]||rawCategory.replace(/_/g," ")||generic(pick(a,"categoria","weapon_category"),/^arma$/i);
  const kind=rawCategory?"":pick(a,"tipo_arma","tipo","weapon_type");
  values=[[...new Set([category,kind].filter(Boolean))].join(" · "),pick(a,"tipo_danno","damage_type"),pick(a,"gittata","portata","range")||[metric(a.gittata_normale_m,"m"),metric(a.gittata_lunga_m,"m")].filter(Boolean).join(" / ")];
  body=completeUnits(props);
  const damageType=values[1];
  const allDescription=stripMeta(completeUnits(description),[["Danno",damage],["Danni",damage],["Tipo di danno",damageType],["Gittata",values[2]],["Costo",pick(a,"costo","cost")],["Peso",pick(a,"peso","weight")||metric(a.peso_kg,"kg")],["Proprietà",text(props)]],[
    "Danni: "+badge+" "+damageType,
    "Danni: "+badge+" "+damageType.replace(/e$/i,"i"),
    "Danno: "+badge+" "+damageType,
    "Danno: "+badge+" "+damageType.replace(/e$/i,"i"),
  ]).filter(unit=>!/^Elenco armi\b/i.test(unit));
  body=[...body,...allDescription.filter(unit=>!body.some(p=>keyText(p)===keyText(unit)))].map(clarifyWeaponProperty);
  const mastery=pick(a,"maestria","proprieta_maestria","mastery");
  if(mastery)body.push("Maestria: "+mastery);
  footer=costWeight;
  break;
 }
 case "armor":{
  const category=pick(a,"categoria_armatura","categoria","tipo","armor_category");
  const shield=/\bscud[oi]\b/i.test(category)||card.reference_type==="shield"||
   (Array.isArray(card.reference_snapshots)&&card.reference_snapshots.some(s=>s?.reference_type==="shield"));
  if(shield)subtitle="Scudo";
  const ac=pick(a,"classe_armatura","ca","armor_class");
  const formula=pick(a,"formula_ca","formula_classe_armatura","ac_formula")||ac;
  const base=(ac||formula).match(/^\s*([+]?\s*\d+)/)?.[1]?.replace(/\s+/g,"")||"";
  badge=shield&&base&&!base.startsWith("+")?"+"+base:base;
  badgeLabel=badge?"CA":"";
  const stealth=yesno(firstRaw(a,"svantaggio_furtivita","furtivita","stealth_disadvantage"));
  values=[shield?"Scudo":cap(generic(category,/^armatura$/i)),
   shield?pick(a,"competenza_scudi","competenze","requisiti","shield_proficiency"):pick(a,"forza_minima","forza","strength_requirement"),
   /^(s[iì]|svantaggio)$/i.test(stealth)?"Svantaggio":/^(no|false|nessuno)$/i.test(stealth)?"":stealth];
  const modifier=armorModifier(formula,badge);
  const cost=pick(a,"costo","cost"),weight=pick(a,"peso","weight")||metric(a.peso_kg,"kg");
  const details=completeUnits(firstRaw(a,"dettagli","proprieta","properties")??description);
  const repeats=[badge?"CA "+badge:"",badge?"CA: "+badge:"",badge?"Bonus "+badge+" alla CA":"",badge?badge+" alla CA":"",
   values[1]?"Forza minima "+values[1]:"",values[2]==="Svantaggio"?"svantaggio alle prove di Furtività":"",
   "Armatura "+category+" (2014)","Armatura "+category+" (2024)","Armatura "+category,
   shield?"Scudo 2014: bonus "+badge+" alla CA":"",shield?"Scudo 2024: bonus "+badge+" alla CA":""];
  body=[modifier,...stripMeta(details,[["CA",ac],["CA",formula],["Costo",cost],["Peso",weight],["Categoria",values[0]],["Requisiti",values[1]],["Furtività",values[2]]],repeats),...completeUnits(note)].filter(Boolean);
  if(!shield&&!modifier&&badge&&/^(?:pesante|armatura pesante)$/i.test(category)&&/^\d+$/.test(formula)){
   body.unshift("CA fissa: non si aggiunge il modificatore di Destrezza.");
  }
  footer=join(costWeight,named("Vestizione",pick(a,"vestizione","tempo_vestizione","tempo_indossare","donning")),named("Rimozione",pick(a,"tempo_togliere","doffing")));
  break;
 }
 default:break;
 }
 return {config,name:text(card.name)||"Senza nome",subtitle,badgeLabel,badge:badge|| (card.type==="feat"?"":"—"),values:values.map(v=>v||"—"),body:[...new Set(body.filter(Boolean))],footer:footer||"—"};
}
