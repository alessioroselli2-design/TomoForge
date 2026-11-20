// A feature is printed from its verified record; the illustration is optional.
// Keep the complete text in the record and in the QR destination.
const readable = value => {
 if (typeof value === "string" || typeof value === "number") return String(value).trim();
 if (Array.isArray(value)) return value.map(readable).filter(Boolean).join(" · ");
 return "";
};
const first = (attrs, keys) => keys.map(key => readable(attrs[key])).find(Boolean) || "";
// Never end a printed teaser halfway through a sentence.
export const featureSentenceExcerpt = (text, max = 700) => {
 const value = String(text || "").trim().replace(/\s+/g, " ");
 if (value.length <= max) return value;
 const ends = [...value.matchAll(/[.!?](?=\s|$)/g)]
   .map(match => match.index + 1).filter(i => i <= max);
 return ends.length ? value.slice(0, ends.at(-1)).trim() :
   "Consulta la descrizione completa della carta.";
};
export const buildFeatureCardView = (card = {}) => {
 const a = card.attributes || {};
 const parentClass = first(a, ["classe","parent_class","class_name","classe_origine"]);
 const level = first(a, ["livello","level","livello_classe","livello_acquisizione"]);
 const description = readable(card.description) || first(a,["descrizione","description","effetto","benefici"]);
 const improvement = first(a, ["miglioramenti","progressione","progressione_livelli","aumento_livello","aumento_al_livello_superiore"]);
 return {
  name: card.name || "Privilegio di classe",
  subtitle: [parentClass, "Privilegio di Classe"].filter(Boolean).join(" • "),
  level,
  description,
  excerpt: featureSentenceExcerpt(description),
  improvement,
  improvementExcerpt: featureSentenceExcerpt(improvement,240),
 };
};
