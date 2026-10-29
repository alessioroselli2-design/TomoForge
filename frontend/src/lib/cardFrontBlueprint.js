// The v2 front is a presentation of existing verified card data, never a new
// source of game rules. One blueprint drives preview, PNG and both PDF modes.
import { typeLabel, attrLabel } from "./cardTypes";
import { getFrontEmblem } from "./frontEmblems";

const THEMES = {
  monster: { accent: "#b5534f", shadow: "#341b28" },
  spell: { accent: "#6e8ee0", shadow: "#1a294b" },
  class: { accent: "#c49b59", shadow: "#322a27" },
  subclass: { accent: "#b2a0e1", shadow: "#302343" },
  feature: { accent: "#9faad8", shadow: "#21283d" },
  race: { accent: "#7fbd99", shadow: "#19352d" },
  feat: { accent: "#d1a46b", shadow: "#36281e" },
  weapon: { accent: "#c5a27d", shadow: "#332829" },
  armor: { accent: "#9fb6c7", shadow: "#243140" },
  item: { accent: "#b18de1", shadow: "#2c2044" },
  character: { accent: "#e2c58e", shadow: "#352c38" },
  custom: { accent: "#a3a3cf", shadow: "#25253b" },
};

const KEYS = {
  monster: [["classe_armatura", "ca", "CA"], ["punti_ferita", "pf", "PF"], ["velocita", "velocità", "Vel."]],
  spell: [["livello", "level", "Liv."], ["tempo_lancio", "azione", "Lancio"], ["gittata", "area", "Gittata"]],
  class: [["dado_vita", "dadi_vita", "Dado vita"], ["abilita_primaria", "caratteristica_primaria", "Primaria"], ["competenze", "tiri_salvezza", "Competenze"]],
  subclass: [["classe", "parent_class", "Classe"], ["livello", "level", "Liv."], ["dado_vita", "abilita_primaria", "Profilo"]],
  feature: [["livello", "level", "Liv."], ["classe", "parent_class", "Classe"], ["azione", "tempo_lancio", "Azione"]],
  race: [["velocita", "velocità", "Vel."], ["taglia", "size", "Taglia"], ["linguaggi", "lingue", "Linguaggi"]],
  feat: [["prerequisito", "prerequisiti", "Requisito"], ["bonus_caratteristiche", "benefici", "Beneficio"]],
  weapon: [["danno", "danni", "Danno"], ["tipo_danno", "categoria", "Tipo"], ["proprieta", "proprietà", "Proprietà"]],
  armor: [["classe_armatura", "ca", "CA"], ["forza_minima", "forza", "Forza"], ["categoria", "tipo", "Tipo"]],
  item: [["rarita", "rarità", "Rarità"], ["sintonia", "richiede_sintonia", "Sintonia"], ["categoria", "tipo", "Tipo"]],
  character: [["classe", "class", "Classe"], ["livello", "level", "Liv."], ["classe_armatura", "ca", "CA"]],
  custom: [["livello", "level", "Liv."], ["categoria", "tipo", "Tipo"]],
};
const DETAIL_KEYS = {
  monster: ["resistenze", "resistenze_danno", "sensi", "azioni", "azioni_speciali", "tratti", "azioni_leggendarie"],
  spell: ["scuola", "componenti", "durata", "concentrazione", "danno", "effetto"],
  class: ["tiri_salvezza", "caratteristiche", "competenze"],
  subclass: ["sottoclasse", "privilegi"],
  feature: ["benefici", "effetto"],
  race: ["tratti_razza", "tratti"],
  feat: ["benefici"],
  weapon: ["proprieta", "gittata", "peso"],
  armor: ["svantaggio_furtivita", "peso"],
  item: ["sintonia", "effetto", "rarita"],
  character: ["razza", "sottoclasse", "bonus_competenza", "cd_incantesimi"],
  custom: ["categoria"],
};
const ABILITY_KEYS = ["for", "des", "cos", "int", "sag", "car"];
// Modifiers are derived from real ability scores using the 5e rule; already
// formatted ability scores, including explicit modifiers, are left unchanged.
const formattedAbility = (value) => {
  const text = String(value).trim();
  if (!/^\d{1,2}$/.test(text)) return text;
  const score = Number(text);
  if (score < 1 || score > 30) return text;
  const modifier = Math.floor((score - 10) / 2);
  return `${score} (${modifier >= 0 ? "+" : ""}${modifier})`;
};
const scalar = (value) => (typeof value === "string" || typeof value === "number") && String(value).trim() !== "";
const readable = (value) => {
  if (scalar(value)) return String(value).trim();
  if (Array.isArray(value)) return value.slice(0, 2).map((entry) => {
    if (scalar(entry)) return String(entry);
    if (entry && typeof entry === "object") return entry.nome || entry.name || "";
    return "";
  }).filter(Boolean).join(" · ");
  return "";
};
const pick = (attrs, names) => names.map((name) => readable(attrs[name])).find(Boolean) || "";
const shortText = (value, max = 62) => String(value || "").length > max
  ? String(value).slice(0, max - 1).trimEnd() + "…"
  : String(value || "");

export const buildFrontBlueprint = (card = {}) => {
  const type = THEMES[card.type] ? card.type : "custom";
  const attrs = card.attributes || {};
  const highlighted = (KEYS[type] || KEYS.custom).map(([first, second, label]) => ({
    label, value: pick(attrs, [first, second]),
  })).filter((entry) => entry.value).slice(0, 3);
  // Never fabricate statistics; empty cells are simply not displayed.
  const highlights = highlighted.map((entry) => ({ ...entry, value: shortText(entry.value, 22) }));
  const abilities = (type === "monster" || type === "character")
    ? ABILITY_KEYS.filter((key) => scalar(attrs[key])).map((key) => ({ label: key.toUpperCase(), value: formattedAbility(attrs[key]) }))
    : [];
  const details = (DETAIL_KEYS[type] || DETAIL_KEYS.custom)
    .map((key) => ({ label: attrLabel(key), value: shortText(readable(attrs[key]), 85), key }))
    .filter((entry) => entry.value)
    .slice(0, type === "monster" ? 3 : (abilities.length ? 2 : 3));
  const heading = typeLabel(type, card.custom_type).toUpperCase();
  const subject = type === "monster"
    ? pick(attrs, ["tipo_creatura", "tipo", "creature_type"])
    : type === "spell" ? pick(attrs, ["scuola", "school"])
      : type === "character" ? pick(attrs, ["classe", "class"])
        : type === "class" || type === "subclass" ? (type === "class" ? card.name : pick(attrs, ["classe", "parent_class"]))
          : type === "race" ? card.name : pick(attrs, ["categoria", "tipo", "parent_class"]);
  // The subtitle names the record, not its category badge or a repeated level.
  // All values originate from actual card attributes.
  const subtitleParts = (() => {
    if (type === "monster") return [
      pick(attrs, ["tipo_creatura", "tipo", "creature_type"]),
      pick(attrs, ["taglia", "size"]),
      pick(attrs, ["allineamento", "alignment"]),
    ];
    if (type === "spell") return [
      pick(attrs, ["classe", "classi", "class", "classes"]),
      pick(attrs, ["scuola", "school"]),
    ];
    if (type === "feature") return [
      pick(attrs, ["classe", "parent_class"]),
      "Privilegio di Classe",
    ];
    if (type === "subclass") return [pick(attrs, ["classe", "parent_class"]), "Sottoclasse"];
    if (type === "character") return [
      pick(attrs, ["classe", "class"]),
      pick(attrs, ["sottoclasse", "subclass"]),
    ];
    if (type === "race") return ["Razza"];
    if (type === "class") return ["Classe"];
    if (type === "feat") return ["Talento"];
    if (type === "item") return [pick(attrs, ["categoria", "tipo"]), "Oggetto Magico"];
    return [subject || heading];
  })().filter(Boolean);
  const subtitle = shortText([...new Set(subtitleParts)].join(" • ") || heading, 80);
  const crest = (subject || heading).replace(/[^a-zA-ZÀ-ÿ ]/g, "").trim().split(/\s+/)
    .filter(Boolean).slice(0, 2).map((token) => token[0].toUpperCase()).join("") || "TF";
  const diceSource = [attrs.danno, attrs.danni, attrs.dadi_vita, attrs.dado_vita, attrs.formula_danno]
    .filter(scalar).map(String).find((value) => /\b\d+d\d+\b/i.test(value)) || "";
  const match = diceSource.match(/\b\d+d\d+(?:\s*[+-]\s*\d+)?\b/i);
  const badge = (() => {
    const text = (value) => (value === null || value === undefined) ? "" : String(value).trim();
    if (type === "monster") return text(attrs.grado_sfida) ? {top:"GS", value:text(attrs.grado_sfida)} : null;
    if (["spell","character","class","subclass","feature"].includes(type))
      return text(attrs.livello) ? {top:"LIV.", value:text(attrs.livello)} : null;
    if (type === "item") return text(attrs.rarita) ? {top:"RARITÀ",value:text(attrs.rarita)} : null;
    return null;
  })();
  const cleanMain = (value) => String(value).split("(")[0].trim();
  const readableStats = highlights.map(item => {
    const original=highlighted.find(x=>x.label===item.label)?.value||item.value;
    let value=item.label==="Vel."?String(original).trim():cleanMain(item.value);
    // Unlike the 19-character trial badge, the speed cell now wraps naturally.
    // Preserve each original movement mode instead of silently dropping it.
    if (item.label==="Vel.") value=value.replace(/volare/ig,"vol.")
      .replace(/nuotare/ig,"nuot.").replace(/scalare/ig,"scal.")
      .replace(/scavare/ig,"scav.");
    return {...item,value:shortText(value,item.label==="Vel."?68:24),fullValue:original};
  });
  return {
    badge, emblem:getFrontEmblem(card),
    type, heading, name: card.name || "Senza nome", subtitle, crest,
    ...THEMES[type], highlights:readableStats, abilities, details,
    dice: match ? match[0].replace(/\s+/g, "") : "",
    description: shortText(card.description, 235),
    hasAbilities: abilities.length > 0,
  };
};
