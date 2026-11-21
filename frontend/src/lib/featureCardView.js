// Privilegi: values are read from the selected TomoForge reference, never from
// class rules guessed by the renderer. The source description is not mutated.
const text = value => {
 if (value === 0) return "0";
 if (value === null || value === undefined || value === false) return "";
 if (typeof value === "string" || typeof value === "number") return String(value).trim();
 if (Array.isArray(value)) return value.map(text).filter(Boolean).join(" · ");
 return "";
};
const first = (a,keys) => keys.map(key=>text(a?.[key])).find(Boolean) || "";
const explicitAction = (description="") => {
 const firstClause=String(description).slice(0,230);
 if (/^(?:come|con) (?:un['’]?)?azione bonus\b/i.test(firstClause)) return "Azione Bonus";
 if (/^(?:come|con) (?:un['’]?)?reazione\b/i.test(firstClause)) return "Reazione";
 if (/^(?:come|con) (?:un['’]?)?azione\b/i.test(firstClause)) return "Azione";
 return "";
};
export const featureSentences = value => {
 const source=String(value||"").replace(/\s+/g," ").trim();
 if (!source) return [];
 const endPositions=[...source.matchAll(/[.!?](?=\s|$)/g)].map(m=>m.index+1);
 return endPositions.map(i=>source.slice(0,i).trim()).filter(Boolean);
};
export const featureSentenceExcerpt = (value,limit=700) => {
 const source=String(value||"").replace(/\s+/g," ").trim();
 if (source.length<=limit) return source;
 return featureSentences(source).filter(s=>s.length<=limit).at(-1)||"";
};
const wildShapeProgression = a => {
 const levels=Array.isArray(a?.limiti_forma_selvatica)?a.limiti_forma_selvatica:[];
 return levels
   .filter(x=>x && x.livello !== undefined && x.gs_max !== undefined)
   .map(x=>({level:Number(x.livello),gs:text(x.gs_max)}))
   .filter(x=>Number.isFinite(x.level)&&x.gs)
   .sort((a,b)=>a.level-b.level)
   .map(x=>x.level+"° livello: GS "+x.gs)
   .join(" · ");
};
export const buildFeatureCardView=(card={})=>{
 const a=card.attributes||{};
 const parent=first(a,["classe","classe_genitore","parent_class","class_name","classe_origine"])
   ||text(card.parent_class);
 const level=first(a,["livello","livello_richiesto","level","livello_classe","livello_acquisizione"])
   ||text(card.level);
 const description=text(card.description)||first(a,["descrizione","description","effetto","benefici"]);
 const activation=first(a,["tipo_attivazione","attivazione","tempo_attivazione",
  "action_type","tipo_azione","activation","activation_type","azione"])
  ||explicitAction(description);
 const uses=first(a,["utilizzi_disponibili","numero_utilizzi","numero_di_utilizzi",
  "utilizzi_per_riposo","utilizzi","usi","uses","cariche","charges"]);
 const recovery=first(a,["recupero_utilizzi","recupero_degli_utilizzi","recupero",
  "ricarica","ripristino_utilizzi","ripristino","recharge","recovery"]);
 const progression=first(a,["progressione","miglioramenti","progressione_livelli",
  "aumento_grado_sfida","aumento_gs","aumento_livello",
  "aumento_al_livello_superiore","livelli_successivi"])
  ||wildShapeProgression(a);
 return {
  name:text(card.name)||"Privilegio di classe",
  subtitle:[parent,"Privilegio di Classe"].filter(Boolean).join(" • "),
  level,description,activation,uses,recovery,progression,
  excerpt:description,
  progressionExcerpt:progression,
  improvement:progression,improvementExcerpt:progression,
 };
};
