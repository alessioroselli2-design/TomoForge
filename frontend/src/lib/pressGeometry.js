import { CARD_ART_SCALE } from "./cardPrintGeometry";

// Default press preset, independent of the existing A4 print options.
// Confirm bleed, corner radius and colour requirements with the print vendor.
export const PRESS_SPEC = Object.freeze({
  trimWidth: 63.5, trimHeight: 88.9, bleed: 3, safe: 3, cornerRadius: 3,
  pageWidth: 69.5, pageHeight: 94.9,
});

export function getPressLayout() {
  const { trimWidth:w, trimHeight:h, bleed:b, safe:s } = PRESS_SPEC;
  // Existing card raster includes a common 2% outer edge. Reduce only enough
  // to keep the original decorated rectangle inside the 3 mm safe rectangle.
  const scale = Math.min(1, (w-2*s)/(w*CARD_ART_SCALE), (h-2*s)/(h*CARD_ART_SCALE));
  return { x:b+(w-w*scale)/2, y:b+(h-h*scale)/2, w:w*scale, h:h*scale };
}

export function setPressPageBoxes(pdf) {
  const { pageWidth:w, pageHeight:h, bleed:b } = PRESS_SPEC;
  const context = pdf.internal.getCurrentPageInfo().pageContext;
  const k = pdf.internal.scaleFactor; // PDF page boxes use points, not mm.
  const box = (x1,y1,x2,y2) => ({
    bottomLeftX:x1*k, bottomLeftY:y1*k, topRightX:x2*k, topRightY:y2*k,
  });
  context.bleedBox = box(0,0,w,h);
  context.trimBox = box(b,b,w-b,h-b);
}
