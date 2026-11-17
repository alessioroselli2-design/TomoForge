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


// One dark-ink icon per primary ability, with a wisdom head/flower for Druid.
export const getClassPrimaryIcon=(value)=>{
 const source=String(value||"").toLowerCase();
 let kind=/sagg/.test(source)?"sag":/intel/.test(source)?"int":
    /caris/.test(source)?"car":/costit/.test(source)?"cos":
    /destr/.test(source)?"des":"for";
 // The source master has a muscle printed at this location. Every variant
 // sits on its own parchment-coloured medallion to replace, not duplicate it.
 const shapes={
  sag:`<path d="M22 5C13 5 7 12 7 21c0 5-3 8-5 11l6 2v15h25v-9c9-6 13-16 9-25C39 8 32 5 22 5Z"/><g fill="#f3d59d" stroke="#231709" stroke-width="1.4"><circle cx="28" cy="20" r="4"/><ellipse cx="28" cy="11" rx="3.5" ry="7"/><ellipse cx="28" cy="29" rx="3.5" ry="7"/><ellipse cx="19" cy="20" rx="7" ry="3.5"/><ellipse cx="37" cy="20" rx="7" ry="3.5"/><circle cx="28" cy="20" r="2.4" fill="#21170e"/></g>`,
  int:`<path d="M10 34c-8-15 0-28 14-28 16 0 24 14 15 28l-6 8H17Z"/><path d="M23 13v21m-7-15 8 3m9-4-8 3m7 8-8-4" fill="none" stroke="#f3d59d" stroke-width="3"/>`,
  car:`<path d="M25 3c-12 0-20 7-20 20s8 21 20 23c12-2 20-10 20-23S37 3 25 3Zm0 8 5 10 11 2-8 8 2 11-10-5-10 5 2-11-8-8 11-2Z" fill-rule="evenodd"/>`,
  cos:`<path d="M25 3 44 11v14c0 13-8 19-19 22C14 44 6 38 6 25V11Z"/><path d="M25 11v28M12 25h26" fill="none" stroke="#f3d59d" stroke-width="3"/>`,
  des:`<path d="M4 26C15 6 35 6 46 26 35 46 15 46 4 26Zm21-12a12 12 0 1 0 0 24 12 12 0 0 0 0-24Zm0 7a5 5 0 1 1 0 10 5 5 0 0 1 0-10Z" fill-rule="evenodd"/>`,
  for:`<path d="M8 39c3-6 4-11 8-13l-1-10c0-3 4-3 5 0l3 7 4-11c2-4 6-1 5 2l-4 11c5-1 10 1 12 6l5 5-6 11H17Z"/>`
 };
 const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50"><circle cx="25" cy="25" r="24" fill="#f3d59d"/><g fill="#21170e">${shapes[kind]}</g></svg>`;
 return "data:image/svg+xml;charset=utf-8,"+encodeURIComponent(svg);
};
