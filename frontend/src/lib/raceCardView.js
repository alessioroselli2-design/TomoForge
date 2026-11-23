// Race cards are a read-only projection of their existing record; no rules are inferred.
const isValue=v=>v!==undefined&&v!==null&&String(v).trim()!=="";
const plain=value=>{
 if(!isValue(value))return "";
 if(typeof value==="string"||typeof value==="number")return String(value).trim();
 if(Array.isArray(value))return value.map(plain).filter(Boolean).join(" · ");
 if(typeof value==="object")return plain(value.valore??value.value??value.nome??value.name??value.testo??value.text??"");
 return "";
};
const first=(attrs,keys)=>keys.map(key=>plain(attrs[key])).find(Boolean)||"";
const traitEntry=(trait)=>{
 if(!trait)return null;
 if(typeof trait==="string")return {name:"",description:trait.trim()};
 if(typeof trait!=="object")return null;
 const name=first(trait,["nome","name","titolo","title","tratto","trait"]);
 const description=first(trait,["descrizione","description","testo","text","effetto","effect","valore","value"]);
 return name||description?{name,description}:null;
};
export const raceTraits=(card={})=>{
 const attrs=card.attributes||{};
 const raw=attrs.tratti_razza??attrs.tratti_razziali??attrs.tratti??attrs.traits;
 if(Array.isArray(raw)){
  const entries=raw.map(traitEntry).filter(Boolean);
  if(entries.length)return entries;
 }
 if(raw&&typeof raw==="object"&&!Array.isArray(raw)){
  const entry=traitEntry(raw);
  if(entry)return [entry];
  return Object.entries(raw).map(([name,value])=>({name,description:plain(value)})).filter(x=>x.description);
 }
 if(typeof raw==="string"&&raw.trim())return raw.trim().split(/\n\s*\n/).map(traitEntry).filter(Boolean);
 // Some imported races have only a plain card.description, not structured traits.
 const fallback=plain(card.description);
 return fallback?[{name:"",description:fallback}]:[];
};
export const raceCardView=(card={})=>{
 const attrs=card.attributes||{};
 const traits=raceTraits(card);
 const directDark=first(attrs,["scurovisione","visione_oscurita","scurovisione_m","scurovisione_metri","darkvision"]);
 const fromTrait=traits.find(x=>/^scurovisione$|^darkvision$/i.test(x.name));
 return {
  name:plain(card.name)||"Senza nome",
  size:first(attrs,["taglia","size"])||"—",
  speed:first(attrs,["velocita","velocità","speed","velocita_base"])||"—",
  darkvision:directDark||(fromTrait?.description||"—"),
  languages:first(attrs,["linguaggi","lingue","languages","language"])||"—",
  traits,
  lineages:first(attrs,["sottorazze","sottorazza","lignaggi","lignaggio","subraces","subrace","lineages","lineage"]),
 };
};
