import {categoryFrontLayout,FRONT_OUTER_MASTER} from "./frontCategoryLayouts";
import {CATEGORY_MASTERS} from "./categoryCardView";
import {frontMasterSlices} from "./cardPrintGeometry";

// Determine the outside of the engraved gold frame from the MASTER, never
// from user art, text, jewels or card data. No extra margin or rescaling.
// These peripheral search bands are deliberately limited so the parchment
// and illustration window cannot be recoloured. The original master remains.
const W=1020,H=1428;
const gold=(p,i)=>p[i]>105 && p[i+1]>75 && p[i+1]>=p[i]*.55 && p[i+2]<p[i+1]*.88;
// Keep every original engraved pixel in its original coordinate. Extend
// ONLY the space outside the silhouette with a continuous rail cross-section
// sampled from the master. Never radially stretch the jewels,
// medallions, scrollwork or parchment.
const SEARCH=.82;
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
export function perimeterPoint(k,w,h){
 const a=w-1,b=h-1,len=2*(a+b);
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
  for(let n=0;n<=Math.ceil(steps*(1-SEARCH));n++){
   const t=1-n/steps,x=Math.round(cx+dx*t),y=Math.round(cy+dy*t);
   if(gold(p,4*(y*w+x))){ray[k]=t;break;}
  }
 }
 const original=ray.slice();
 for(let k=0;k<len;k++){
  if(ray[k])continue;
  for(let d=1;d<=Math.max(2,Math.round(Math.min(w,h)*.06));d++){
   const a=original[(k-d+len)%len],b=original[(k+d)%len];
   if(a||b){ray[k]=a&&b?(a+b)/2:a||b;break;}
  }
  if(!ray[k])ray[k]=.96;
 }
 return ray;
}
// Median cross-section from an actual continuous side of the master.
const median=a=>{a.sort((x,y)=>x-y);return a[Math.floor(a.length/2)];};
export function sampleRailProfile(p,w,h){
 const thickness=Math.max(3,Math.round(w*.019)),search=Math.max(3,Math.round(w*.085));
 const span=Math.max(5,Math.round(h*.10)),stride=Math.max(1,Math.round(span/5));
 let best=null;
 for(const side of [0,1]){
  const first=new Int32Array(h).fill(-1);
  const at=(y,d)=>4*(y*w+(side?w-1-d:d));
  for(let y=0;y<h;y++)for(let d=0;d<search;d++){if(gold(p,at(y,d))){first[y]=d;break;}}
  for(let y=Math.round(h*.20);y+span<h*.88;y+=stride){
   const valid=[];for(let j=y;j<y+span;j++)if(first[j]>=0)valid.push(first[j]);
   if(valid.length<span*.95)continue;
   const d=median(valid);let score=0;
   for(let j=y;j<y+span;j++){
    score-=Math.abs(first[j]-d)*8;
    for(let q=0;q<thickness;q++){
     const i=at(j,d+q);score+=gold(p,i)?2:(p[i]>100&&p[i+1]<p[i]*.32?-5:0);
    }
   }
   score+=span*(y/h>.68?1:0);
   if(!best||score>best.score)best={y,d,side,score};
  }
 }
 if(!best)return [[183,113,35],[238,185,83],[99,48,12],[44,17,6]];
 const profile=[];
 for(let q=0;q<thickness;q++){
  const channels=[[],[],[]];
  for(let y=best.y;y<best.y+span;y++){
   const x=best.side?w-1-best.d-q:best.d+q,i=4*(y*w+clamp(x,0,w-1));
   for(let j=0;j<3;j++)channels[j].push(p[i+j]);
  }
  profile.push(channels.map(median));
 }
 return profile;
}
export function roundedTrimDistance(x,y,w,h){
 const r=w*3/63.5,cx=(w-1)/2,cy=(h-1)/2;
 const qx=Math.abs(x-cx)-(cx-r),qy=Math.abs(y-cy)-(cy-r);
 const d=r-Math.hypot(Math.max(qx,0),Math.max(qy,0))-Math.min(Math.max(qx,qy),0);
 return Math.abs(d)<1e-8?0:d;
}
export function exteriorAlpha(p,w,h){
 const cx=(w-1)/2,cy=(h-1)/2,a=w-1,b=h-1;
 const trace=traceOuterRail(p,w,h),len=trace.length,profile=sampleRailProfile(p,w,h);
 const width=Math.max(2,w*.009),shadow=[44,17,6];
 const result=new Uint8ClampedArray(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const dx=x-cx,dy=y-cy,t=Math.max(Math.abs(dx)/cx,Math.abs(dy)/cy);
  if(t<=SEARCH)continue;
  const ex=clamp(cx+dx/t,0,a),ey=clamp(cy+dy/t,0,b);
  const k=Math.abs(dy)/cy>=Math.abs(dx)/cx?(dy<0?ex:a+b+(a-ex)):(dx>0?a+ey:2*a+b+(b-ey));
  const k0=Math.floor(k)%len,k1=(k0+1)%len;
  const edge=trace[k0]+(trace[k1]-trace[k0])*(k-Math.floor(k));
  const i=4*(y*w+x),guard=1/Math.max(Math.abs(ex-cx),Math.abs(ey-cy));
  // No original pixels within the traced ornament contour are resampled.
  if(t<=edge+guard||gold(p,i))continue;
  const d=roundedTrimDistance(x,y,w,h);
  const z=clamp(d/Math.max(1,width-1),0,1)*(profile.length-1),j=Math.floor(z),frac=z-j;
  const col=profile[j].map((v,q)=>v*(1-frac)+profile[Math.min(j+1,profile.length-1)][q]*frac);
  const blend=d<0?0:clamp(width-d,0,1);
  for(let q=0;q<3;q++)result[i+q]=Math.round(shadow[q]*(1-blend)+col[q]*blend);
  result[i+3]=255;
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
