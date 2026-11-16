export const CLASS_STAT_ICONS=Object.freeze({
  "Abilità primaria":"/card-art/class-stats/primary-v33.svg",
  "Tiri salvezza":"/card-art/class-stats/saves-v33.svg",
  "Competenze":"/card-art/class-stats/proficiencies-v33.svg",
});
export const getClassStatIcon=(label)=>CLASS_STAT_ICONS[label]||null;
