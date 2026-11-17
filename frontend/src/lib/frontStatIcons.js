// Approved CA/PF symbols isolated from their black disks as warm-ink SVG runes.
// The ornate golden wells are part of the v17 master and are never duplicated.
export const getFrontStatIcon = (label) => {
  const key = String(label || "").trim().toUpperCase();
  if (key === "CA") return "/card-art/stat-ca-clean-v24.svg";
  if (key === "PF") return "/card-art/stat-pf-clean-v24.svg";
  if (key === "ABILITÀ PRIMARIA") return "/card-art/class-stats/primary-v33.svg";
  if (key === "TIRI SALVEZZA") return "/card-art/class-stats/saves-v33.svg";
  if (key === "COMPETENZE") return "/card-art/class-stats/proficiencies-v33.svg";
  return null;
};

// The raster Class master engraves the strength arm by default; only
// non-strength primary abilities need a single opaque parchment-backed stamp.
export const getClassAbilityIcon=(raw)=>{
 const text=String(raw||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
 if(/forza|strength/.test(text))return "";
 if(/saggezza|wisdom/.test(text))return "/card-art/class-stats/primary-saggezza.svg";
 if(/destrezza|dexterity/.test(text))return "/card-art/class-stats/primary-destrezza.svg";
 if(/intelligenza|intelligence/.test(text))return "/card-art/class-stats/primary-intelligenza.svg";
 if(/carisma|charisma/.test(text))return "/card-art/class-stats/primary-carisma.svg";
 if(/costituzione|constitution/.test(text))return "/card-art/class-stats/primary-costituzione.svg";
 return "";
};
