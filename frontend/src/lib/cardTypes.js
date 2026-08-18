import { Sparkles, Shield, Users, Sword, Award, Skull, User, Wand2 } from "lucide-react";

export const CARD_TYPES = [
  { id: "spell", label: "Magia", icon: Sparkles },
  { id: "class", label: "Classe", icon: Shield },
  { id: "race", label: "Razza", icon: Users },
  { id: "weapon", label: "Arma", icon: Sword },
  { id: "feat", label: "Talento", icon: Award },
  { id: "monster", label: "Mostro", icon: Skull },
  { id: "character", label: "Personaggio", icon: User },
  { id: "custom", label: "Personalizzato", icon: Wand2 },
];

export const typeLabel = (id, custom) => {
  if (id === "custom" && custom) return custom;
  return CARD_TYPES.find((t) => t.id === id)?.label || id;
};

export const typeIcon = (id) => CARD_TYPES.find((t) => t.id === id)?.icon || Wand2;

// Human labels for attribute keys (Italian)
export const ATTR_LABELS = {
  livello: "Livello", scuola: "Scuola", azione: "Azione", tempo_lancio: "Tempo di lancio", gittata: "Gittata",
  area: "Area", componenti: "Componenti", durata: "Durata", concentrazione: "Concentrazione", danno: "Danno", effetto: "Effetto",
  dado_vita: "Dado vita", abilita_primaria: "Abilità primaria", tiri_salvezza: "Tiri salvezza",
  competenze: "Competenze", caratteristiche: "Caratteristiche",
  bonus_caratteristiche: "Bonus caratteristiche", velocita: "Velocità", taglia: "Taglia",
  linguaggi: "Linguaggi", tratti: "Tratti",
  danno: "Danno", tipo_danno: "Tipo di danno", proprieta: "Proprietà", peso: "Peso",
  costo: "Costo", categoria: "Categoria",
  prerequisito: "Prerequisito", benefici: "Benefici",
  classe_armatura: "Classe Armatura (CA)", punti_ferita: "Punti Ferita (PF)",
  for: "FOR", des: "DES", cos: "COS", int: "INT", sag: "SAG", car: "CAR",
  resistenze: "Resistenze", vulnerabilita: "Vulnerabilità", immunita: "Immunità",
  sensi: "Sensi", grado_sfida: "Grado Sfida", azioni: "Azioni",
  classe: "Classe", razza: "Razza", bonus_competenza: "Bonus competenza",
  cd_incantesimi: "CD incantesimi", abilita_sottoclasse: "Abilità sottoclasse",
  slot_incantesimi: "Slot incantesimi", nome: "Nome", descrizione: "Descrizione",
  totale: "Totale", usati: "Usati",
};

export const attrLabel = (k) => ATTR_LABELS[k] || k.replace(/_/g, " ");

// Fields shown as quick gameplay reference on the CARD FRONT (in order), per type.
// The full detail (and remaining fields) live on the detail page / QR.
export const QUICK_FIELDS = {
  spell: ["livello", "azione", "gittata", "area", "concentrazione", "danno"],
  weapon: ["danno", "tipo_danno", "proprieta", "categoria"],
  feat: ["prerequisito"],
  class: ["dado_vita", "abilita_primaria"],
  race: ["velocita", "taglia"],
  monster: ["classe_armatura", "punti_ferita", "grado_sfida", "velocita"],
  character: ["classe", "livello", "classe_armatura", "punti_ferita"],
};

export const EMBLEMS = [
  { id: "flame", label: "Fiamma" },
  { id: "skull", label: "Teschio" },
  { id: "dragon", label: "Drago" },
  { id: "sword", label: "Spada" },
  { id: "moon", label: "Luna" },
  { id: "eye", label: "Occhio" },
  { id: "shield", label: "Scudo" },
  { id: "star", label: "Stella" },
];

export const BACK_STYLES = [
  { id: "classic", label: "Classico" },
  { id: "runic", label: "Runico" },
  { id: "damask", label: "Damascato" },
  { id: "arcane", label: "Arcano" },
];
