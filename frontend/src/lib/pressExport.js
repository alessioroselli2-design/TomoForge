import { CARD_EDGE_COLOR } from "./cardPrintGeometry";
import { PRESS_SPEC, getPressLayout, setPressPageBoxes } from "./pressGeometry";
import { renderCardCanvas, renderCardBackCanvas } from "./cardExport";

export { PRESS_SPEC };

export function addPressFace(pdf, canvas) {
  const {pageWidth,pageHeight}=PRESS_SPEC;
  const {x,y,w,h}=getPressLayout();
  setPressPageBoxes(pdf);
  // Extend the real common edge through bleed. No white lines, crop marks,
  // mirroring, corner clipping or resampling of the source raster.
  pdf.setFillColor(CARD_EDGE_COLOR);
  pdf.rect(0,0,pageWidth,pageHeight,"F");
  pdf.addImage(canvas.toDataURL("image/png"),"PNG",x,y,w,h);
}

// Ordered pages: front, corresponding upright back, then the next card.
// A missing renderer aborts the entire file rather than producing a broken pair.
export async function addPressCardPages(pdf, element, card, {first=true}={}) {
  const front=await renderCardCanvas(element,card);
  const back=await renderCardBackCanvas(card);
  if(!first)pdf.addPage([PRESS_SPEC.pageWidth,PRESS_SPEC.pageHeight],"portrait");
  addPressFace(pdf,front);
  pdf.addPage([PRESS_SPEC.pageWidth,PRESS_SPEC.pageHeight],"portrait");
  addPressFace(pdf,back);
  return {front,back};
}
