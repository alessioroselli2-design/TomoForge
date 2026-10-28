// Ten official, user-approved TomeForge backs. All assets share the 5:7 card ratio.
// Never use the deprecated runic/damask emblems or a custom color for the reverse.
export const CHARACTER_BACK_VARIANTS = Object.freeze([
  { id: "luminous", label: "Figura luminosa (avorio e oro)" },
  { id: "silver", label: "Elmo bianco e argento" },
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
  weapon: ["armi-armature", "Armi e armature"],
  armor: ["armi-armature", "Armi e armature"],
  shield: ["armi-armature", "Armi e armature"],
  item: ["oggetto-magico", "Oggetti magici"],
  magic_item: ["oggetto-magico", "Oggetti magici"],
  character: ["personaggio-luce", "Personaggio"],
  // A custom card has no tenth category of its own; it uses the neutral
  // approved magic-item back rather than an unapproved invented design.
  custom: ["oggetto-magico", "Personalizzato"],
});

export const getApprovedBack = (card = {}) => {
  const type = typeof card?.type === "string" ? card.type.toLowerCase() : "custom";
  const [defaultFile, label] = BACKS[type] || BACKS.custom;
  const isCharacter = type === "character";
  const variant = isCharacter && card.back?.variant === "silver" ? "silver" : "luminous";
  const file = isCharacter && variant === "silver" ? "personaggio-argento" : defaultFile;

  return { file, src: `/dorsi/${file}.jpg`, label, variant };
};
