// The only official TomoForge reverses. Artwork lives in /public/dorsi/ and
// is selected by the actual card category, never by legacy saved styles.
export const CHARACTER_BACK_VARIANTS = Object.freeze([
  { id: "luminous", label: "Figura luminosa (avorio e oro)" },
  { id: "silver", label: "Elmo bianco e argento" },
]);

export const APPROVED_BACK_FILES = Object.freeze([
  "mostro", "classe", "talento", "incantesimo", "armi-armature",
  "privilegio", "razza", "personaggio-luce", "personaggio-argento",
  "oggetto-magico",
]);

const BACKS = Object.freeze({
  monster: ["mostro", "Mostri"],
  class: ["classe", "Classi"],
  subclass: ["classe", "Classi"],
  class_feature: ["privilegio", "Privilegi"],
  feature: ["privilegio", "Privilegi"],
  spell: ["incantesimo", "Incantesimi"],
  feat: ["talento", "Talenti"],
  race: ["razza", "Razze"],
  subrace: ["razza", "Razze"],
  weapon: ["armi-armature", "Armi, armature e scudi"],
  armor: ["armi-armature", "Armi, armature e scudi"],
  shield: ["armi-armature", "Armi, armature e scudi"],
  item: ["oggetto-magico", "Oggetti magici"],
  magic_item: ["oggetto-magico", "Oggetti magici"],
  character: ["personaggio-luce", "Personaggio"],
  // Custom cards do not introduce an eleventh back; use the approved neutral one.
  custom: ["oggetto-magico", "Personalizzato"],
});

export const getApprovedBack = (card = {}) => {
  const type = typeof card?.type === "string" ? card.type.trim().toLowerCase() : "custom";
  const [defaultFile, label] = BACKS[type] || BACKS.custom;
  const isCharacter = type === "character";
  const variant = isCharacter && card?.back?.variant === "silver" ? "silver" : "luminous";
  const file = isCharacter && variant === "silver" ? "personaggio-argento" : defaultFile;

  return { file, src: `/dorsi/${file}.jpg`, label, variant };
};
