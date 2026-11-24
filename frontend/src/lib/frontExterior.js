import {categoryFrontLayout,FRONT_OUTER_MASTER} from "./frontCategoryLayouts";
import {CATEGORY_MASTERS} from "./categoryCardView";
import {frontMasterSlices} from "./cardPrintGeometry";

// Determine the outside of the engraved gold frame from the MASTER, never
// from user art, text, jewels or card data. No extra margin or rescaling.
// These peripheral search bands are deliberately limited so the parchment
// and illustration window cannot be recoloured. The original master remains.
const W=1020,H=1428;
const gold=(p,i)=>p[i]>105 && p[i+1]>75 && p[i+1]>=p[i]*.55 && p[i+2]<p[i+1]*.88;
// Geometric extension of the original engraving. Each ray from the card
// centre meets the rectangular cut line. Locate the first real gold pixel
// on that ray and expand the narrow original outer rail to the cut line.
// All pixels inside the fixed inner contour are untouched. No invented
// colours, texture, second frame, or scaling of the entire card.
const INNER=.90, SEARCH=.82;
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
export function perimeterPoint(k,w,h){
 const a=w-1,b=h-1, len=2*(a+b);
 k=((k%len)+len)%len;
 if(k<a)return [k,0];
 k-=a;if(k<b)return [a,k];
 k-=b;if(k<a)return [a-k,b];
 k-=a;return [0,b-k];
}
export function traceOuterRail(p,w,h){
 const cx=(w-1)/2,cy=(h-1)/2,len=2*(w+h-2);
 const ray=new Float32Array(len);
 for(let k=0;k<len;k++){
  const [ex,ey]=perimeterPoint(k,w,h);
  const dx=ex-cx,dy=ey-cy,steps=Math.max(Math.abs(dx),Math.abs(dy));
  let found=0;
  for(let n=0;n<=Math.ceil(steps*(1-SEARCH));n++){
   const t=1-n/steps, x=Math.round(cx+dx*t),y=Math.round(cy+dy*t);
   if(gold(p,4*(y*w+x))){found=t;break;}
  }
  ray[k]=found;
 }
 // Fill tiny gaps in the trace from adjoining portions of the same rail.
 // Use the actual sampled ray whenever available; do not invent a palette.
 for(let k=0;k<len;k++){
  if(ray[k])continue;
  let v=0;
  for(let d=1;d<=Math.round(Math.min(w,h)*.06);d++){
   const a=ray[(k-d+len)%len],b=ray[(k+d)%len];
   if(a||b){v=a&&b?(a+b)/2:a||b;break;}
  }
  ray[k]=v||.96;
 }
 return ray;
}
function readPixel(p,w,h,x,y,out,i){
 x=clamp(x,0,w-1);y=clamp(y,0,h-1);
 const x0=Math.floor(x),y0=Math.floor(y),x1=Math.min(w-1,x0+1),y1=Math.min(h-1,y0+1);
 const fx=x-x0,fy=y-y0;
 for(let q=0;q<3;q++){
  const a=p[4*(y0*w+x0)+q]*(1-fx)+p[4*(y0*w+x1)+q]*fx;
  const b=p[4*(y1*w+x0)+q]*(1-fx)+p[4*(y1*w+x1)+q]*fx;
  out[i+q]=Math.round(a*(1-fy)+b*fy);
 }
 out[i+3]=255;
}
export function exteriorAlpha(p,w,h){
 const cx=(w-1)/2,cy=(h-1)/2,a=w-1,b=h-1;
 const trace=traceOuterRail(p,w,h),len=trace.length;
 const result=new Uint8ClampedArray(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const dx=x-cx,dy=y-cy,t=Math.max(Math.abs(dx)/cx,Math.abs(dy)/cy);
  if(t<=INNER)continue;
  const ex=clamp(cx+dx/t,0,a),ey=clamp(cy+dy/t,0,b);
  let k;
  if(Math.abs(dy)/cy>=Math.abs(dx)/cx)k=dy<0?ex:a+b+(a-ex);
  else k=dx>0?a+ey:2*a+b+(b-ey);
  const k0=Math.floor(k)%len,k1=(k0+1)%len;
  const edge=trace[k0]+(trace[k1]-trace[k0])*(k-Math.floor(k));
  // Anchor the inside of the outer rail; widen only its original pixels.
  const inner=Math.min(INNER,edge-.035);
  const u=clamp((t-inner)/(1-inner),0,1);
  const sourceT=inner+(edge-inner)*u;
  const i=4*(y*w+x);
  readPixel(p,w,h,cx+dx/t*sourceT,cy+dy/t*sourceT,result,i);
 }
 return result;
}

export function frontMaskSource(type) {
 const dedicated={spell:"master-incantesimo-5x7-v1.webp",feature:"master-privilegi-5x7.png",race:"master-razze-5x7.png"};
 const asset=dedicated[type]||CATEGORY_MASTERS[type]?.master;
 if(asset)return {src:"/card-art/"+asset,legacy:false,type};
 const normalized=type==="subclass"?"class":type;
 return {src:categoryFrontLayout(normalized).master||FRONT_OUTER_MASTER,legacy:true,type:normalized};
}
const cache=new Map();
export function getFrontExteriorMask(type) {
 const spec=frontMaskSource(type), key=spec.src+"|"+(spec.legacy?spec.type:"dom");
 if(cache.has(key))return cache.get(key);
 const pending=(async()=>{
   const image=new Image();
   await new Promise((resolve,reject)=>{
    image.onload=resolve;image.onerror=()=>reject(new Error("Cornice fronte non disponibile"));
    image.src=spec.src;if(image.complete&&image.naturalWidth)resolve();
   });
   const master=document.createElement("canvas");master.width=W;master.height=H;
   const ctx=master.getContext("2d");
   if(!ctx||typeof ctx.getImageData!=="function")return null;
   ctx.drawImage(image,0,0,W,H);
   if(spec.legacy){
     const iw=image.naturalWidth,ih=image.naturalHeight||iw*7/5;
     frontMasterSlices(spec.type).forEach(s=>ctx.drawImage(image,0,s.sourceY*ih,iw,s.sourceH*ih,0,s.y*H,W,s.h*H));
   }
   const rgba=ctx.getImageData(0,0,W,H);
   const mask=document.createElement("canvas");mask.width=W;mask.height=H;
   const out=mask.getContext("2d"),data=out.createImageData(W,H);
   data.data.set(exteriorAlpha(rgba.data,W,H));out.putImageData(data,0,0);
   return mask;
 })();
 cache.set(key,pending);
 pending.catch(()=>cache.delete(key));
 return pending;
}
export async function colorFrontExterior(canvas,type) {
 const ctx=canvas.getContext("2d");
 // Minimal canvas mocks do not expose pixel APIs; production canvases do.
 if(typeof ctx.getImageData!=="function")return canvas;
 const mask=await getFrontExteriorMask(type);
 if(!mask)throw new Error("Maschera cornice non disponibile");
 ctx.save();ctx.setTransform(1,0,0,1,0,0);
 ctx.globalCompositeOperation="source-over";
 ctx.drawImage(mask,0,0,canvas.width,canvas.height);ctx.restore();
 return canvas;
}
