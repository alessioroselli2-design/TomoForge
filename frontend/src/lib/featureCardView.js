// Verified card data is the only source for feature fields: never guess counts or rest rules.
const readable = value => {
 if (typeof value === "string" || typeof value === "number") return String(value).trim();
 if (Array.isArray(value)) return value.map(readable).filter(Boolean).join(" · ");
 if (value && typeof value === "object") return readable(value.value ?? value.max ?? value.name ?? "");
 return "";
};
const first = (attrs, keys) => keys.map(key => readable(attrs[key])).find(Boolean) || "";
export const featureSentenceExcerpt = (text, max = 700) => {
 const value = String(text || "").trim().replace(/\s+/g, " ");
 if (value.length <= max) return value;
 const ends = [...value.matchAll(/[.!?](?=\s|$)/g)]
   .map(match => match.index + 1).filter(i => i <= max);
 return ends.length ? value.slice(0, ends.at(-1)).trim() : "Descrizione completa disponibile tramite QR.";
};
const inferExplicitActivation = description => {
 const start = String(description || "").trim().toLowerCase();
 if (/^(come|con) (un['’]?)?azione bonus\b/.test(start)) return "Azione bonus";
 if (/^(come|con) (un['’]?)?reazione\b/.test(start)) return "Reazione";
 if (/^(come|con) (un['’]?)?azione\b/.test(start)) return "Azione";
 return "";
};
export const buildFeatureCardView = (card = {}) => {
 const attrs = card.attributes || {};
 const parentClass = first(attrs, ["classe", "parent_class", "class_name", "classe_origine"]);
 const level = first(attrs, ["livello", "level", "livello_classe", "livello_acquisizione"]);
 const description = readable(card.description) || first(attrs, ["descrizione", "description", "effetto", "benefici"]);
 const activation = first(attrs, [
  "tipo_attivazione", "attivazione", "tempo_attivazione", "action_type",
  "tipo_azione", "activation", "activation_type", "azione",
 ]) || inferExplicitActivation(description);
 const uses = first(attrs, [
  "utilizzi_disponibili", "numero_utilizzi", "numero_di_utilizzi",
  "utilizzi", "usi", "uses", "cariche", "charges"
 ]);
 const recovery = first(attrs, [
  "recupero_utilizzi", "recupero_degli_utilizzi", "recupero", "ricarica",
  "ripristino_utilizzi", "ripristino", "recharge", "recovery"
 ]);
 const progression = first(attrs, [
  "progressione", "miglioramenti", "progressione_livelli",
  "aumento_grado_sfida", "aumento_gs", "aumento_livello",
  "aumento_al_livello_superiore", "livelli_successivi"
 ]);
 return {
  name:card.name || "Privilegio di classe",
  subtitle:[parentClass, "Privilegio di Classe"].filter(Boolean).join(" • "),
  level, description, excerpt:featureSentenceExcerpt(description),
  activation, uses, recovery, progression,
  progressionExcerpt:featureSentenceExcerpt(progression,230),
  // Backward-compatible aliases for existing consumers
  improvement:progression, improvementExcerpt:featureSentenceExcerpt(progression,230),
 };
};
