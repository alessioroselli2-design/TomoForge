// Medallions cropped from the user's approved Drago Rosso Adulto reference.
// Both transparent WebP assets preserve the original icon, black center and gold rim.
export const getFrontStatIcon = (label) => {
  const key = String(label || "").trim().toUpperCase();
  if (key === "CA") return "/card-art/stat-ca.webp";
  if (key === "PF") return "/card-art/stat-pf.webp";
  return null;
};
