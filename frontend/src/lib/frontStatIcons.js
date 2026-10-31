// Approved CA/PF symbols isolated from their black disks as warm-ink SVG runes.
// The ornate golden wells are part of the v17 master and are never duplicated.
export const getFrontStatIcon = (label) => {
  const key = String(label || "").trim().toUpperCase();
  if (key === "CA") return "/card-art/stat-ca-clean-v24.svg";
  if (key === "PF") return "/card-art/stat-pf-clean-v24.svg";
  return null;
};
