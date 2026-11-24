// Common physical edge and calibrated optical centering. Do not stretch
// or alter the approved masters, typography, emblem or interior coordinates.
export const CARD_EDGE_COLOR = "#101019";
export const CARD_ART_INSET = 0.02;
export const CARD_ART_SCALE = 1 - 2 * CARD_ART_INSET;
const SOURCE_WIDTH=750, SOURCE_HEIGHT=1050;

// The Monster master has a redundant lava strip below its gold frame.
// Shift the whole rendered face down, clipping ONLY the redundant last 3%.
// Keep y <= 97%: the existing legacy QR ends at 456/476 (95.8%).
// Class and Spell have a smaller surplus strip. Unmeasured masters are left intact.
export function frontOpticalShift(type) {
  if (["monster","character","custom"].includes(type)) return .03;
  if (["class","subclass","spell"].includes(type)) return .008;
  return 0;
}

export function cardArtBounds(width,height) {
  return {x:width*CARD_ART_INSET,y:height*CARD_ART_INSET,w:width*CARD_ART_SCALE,h:height*CARD_ART_SCALE};
}

// Class includes an outer photographic surround. Remove the surplus right
// edge only; keep every original top/bottom pixel, including the central tips.
// The other nine official backs reach the top edge in the original file.
// Provide 24 source pixels of additional headroom and reconstruct the missing
// central cap using the vertically reflected bottom ornament (same artwork).
export function getBackComposition(file,width=SOURCE_WIDTH,height=SOURCE_HEIGHT) {
  const standard=Math.abs(width/height-5/7)<.001;
  const k=width/SOURCE_WIDTH;
  const crop=file==="classe"&&standard?{x:0,y:0,w:725*k,h:height}:{x:0,y:0,w:width,h:height};
  const extension=standard&&file!=="classe"?24*k:0;
  const fit=Math.min(width/crop.w,height/(crop.h+extension));
  const w=crop.w*fit,h=crop.h*fit;
  const x=(width-w)/2,y=(height-(crop.h+extension)*fit)/2+extension*fit;
  // The bottom point is available on the original. Reflect only a narrow
  // triangular central cap outside the original image, not the book or text.
  const tip=extension?{sx:width/2-36*k,sy:height-extension,sw:72*k,sh:extension,
    x:width/2-36*k*fit,y:y-extension*fit,w:72*k*fit,h:extension*fit}:null;
  return {crop,x,y,w,h,tip,fit};
}

export function backImageStyle(file) {
  const c=getBackComposition(file);
  return {left:100*(c.x-c.crop.x*c.fit)/SOURCE_WIDTH+"%",
    top:100*(c.y-c.crop.y*c.fit)/SOURCE_HEIGHT+"%",
    width:100*c.fit+"%",height:100*c.fit+"%",maxWidth:"none",objectFit:"fill",
    clipPath:file==="classe"?"inset(0 3.333333% 0 0)":undefined};
}

export function backTipStyles(file) {
  const c=getBackComposition(file);
  if(!c.tip)return null;
  const t=c.tip;
  return {
    box:{position:"absolute",left:100*t.x/SOURCE_WIDTH+"%",top:100*t.y/SOURCE_HEIGHT+"%",
      width:100*t.w/SOURCE_WIDTH+"%",height:100*t.h/SOURCE_HEIGHT+"%",
      overflow:"hidden",clipPath:"polygon(50% 0, 100% 100%, 0 100%)",pointerEvents:"none"},
    image:{position:"absolute",left:-100*t.sx/t.sw+"%",
      width:100*SOURCE_WIDTH/t.sw+"%",height:100*SOURCE_HEIGHT/t.sh+"%",
      maxWidth:"none",transform:"scaleY(-1)",transformOrigin:"center",objectFit:"fill",
      top:0}
  };
}

// Back image is already in the target 5:7 canvas. This common final
// operation is also used by every front path, including the real DOM render.
export function applyCardPrintEdge(canvas,shift=0) {
  const ctx=canvas.getContext("2d");
  const {width,height}=canvas;
  const {x,y,w,h}=cardArtBounds(width,height);
  ctx.save();
  ctx.setTransform(1,0,0,1,0,0);
  ctx.globalCompositeOperation="copy";
  if(shift)ctx.drawImage(canvas,0,0,width,height*(1-shift),x,y+h*shift,w,h*(1-shift));
  else ctx.drawImage(canvas,x,y,w,h);
  ctx.globalCompositeOperation="destination-over";
  ctx.fillStyle=CARD_EDGE_COLOR;
  ctx.fillRect(0,0,width,height);
  ctx.restore();
  return canvas;
}
