import { PRESS_SPEC, getPressLayout, setPressPageBoxes } from "./pressGeometry";
import { renderCardCanvas, renderCardBackCanvas } from "./cardExport";

export { PRESS_SPEC };

// Extend the actual edge pixels only OUTSIDE trim. No shrinking or dark rim.
// The original full-size raster is drawn again at exact trim in PDF units.
export function makePressBleed(canvas) {
 const p=PRESS_SPEC, b=document.createElement("canvas");
 const w=canvas.width,h=canvas.height;
 const dx=Math.ceil(w*p.bleed/p.trimWidth),dy=Math.ceil(h*p.bleed/p.trimHeight);
 b.width=w+2*dx;b.height=h+2*dy;
 const c=b.getContext("2d");
 c.drawImage(canvas,dx,dy);
 for(const [sx,x] of [[0,0],[w-1,dx+w]])
   c.drawImage(canvas,sx,0,1,h,x,dy,dx,h);
 for(const [sy,y] of [[0,0],[h-1,dy+h]])
   c.drawImage(canvas,0,sy,w,1,dx,y,w,dy);
 for(const [sx,x] of [[0,0],[w-1,dx+w]])for(const [sy,y] of [[0,0],[h-1,dy+h]])
   c.drawImage(canvas,sx,sy,1,1,x,y,dx,dy);
 return b;
}

export function addPressFace(pdf, canvas) {
 const {pageWidth,pageHeight}=PRESS_SPEC;
 const {x,y,w,h}=getPressLayout();
 setPressPageBoxes(pdf);
 const bleed=makePressBleed(canvas);
 pdf.addImage(bleed.toDataURL("image/png"),"PNG",0,0,pageWidth,pageHeight);
 pdf.addImage(canvas.toDataURL("image/png"),"PNG",x,y,w,h);
}

// Ordered pages: front, corresponding upright back, then the next card.
// A missing renderer aborts the entire file rather than producing a broken pair.
export async function addPressCardPages(pdf, element, card, {first=true,frontLayers}={}) {
  const front=await renderCardCanvas(element,card,frontLayers);
  const back=await renderCardBackCanvas(card);
  if(!first)pdf.addPage([PRESS_SPEC.pageWidth,PRESS_SPEC.pageHeight],"portrait");
  addPressFace(pdf,front);
  pdf.addPage([PRESS_SPEC.pageWidth,PRESS_SPEC.pageHeight],"portrait");
  addPressFace(pdf,back);
  return {front,back};
}
