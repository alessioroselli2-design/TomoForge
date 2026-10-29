// Stable production address: printed QR codes must work outside protected preview URLs.
// Only saved cards have a shareable, public detail page; never publish a private
// library record identifier or a draft's unsaved contents.
export const publicDescriptionUrl = (card) => {
  const id = card?.id;
  if (typeof id !== "string" || !id.trim()) return "";
  return `https://tomo-forge.vercel.app/d/${encodeURIComponent(id.trim())}`;
};
