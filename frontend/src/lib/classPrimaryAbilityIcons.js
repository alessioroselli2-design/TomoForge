// Class-only symbols, read from the actual verified record value.
const NAMES = ["forza","destrezza","costituzione","intelligenza","saggezza","carisma"];
export const getClassPrimaryAbilityIcons = (value) => {
  const normalized = String(value ?? "").normalize("NFD")
    .replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("it-IT");
  const found = normalized.match(/\b(forza|destrezza|costituzione|intelligenza|saggezza|carisma)\b/g) || [];
  return [...new Set(found)].slice(0,2).filter(name=>NAMES.includes(name))
    .map(name=>({name,src:`/icone-caratteristiche/${name}.png`}));
};
