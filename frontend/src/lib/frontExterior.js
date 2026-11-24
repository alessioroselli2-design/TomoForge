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
// ONLY the space outside the silhouette with a small real straight-rail
// section sampled from the master. Never radially stretch the jewels,
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
// A side is parameterised by position along the edge and inward depth.
function sideIndex(side,t,d,w,h){
 const x=side===0||side===2?t:side===1?w-1-d:d;
 const y=side===1||side===3?t:side===0?d:h-1-d;
 return 4*(clamp(Math.round(y),0,h-1)*w+clamp(Math.round(x),0,w-1));
}
function warm(p,i){
 return p[i]>50&&p[i+1]>=p[i]*.48&&p[i+2]<p[i+1]*.92;
}
function ruby(p,i){
 return p[i]>95&&p[i+1]<p[i]*.42&&p[i+2]<p[i]*.68;
}
// Find a real, quiet section of each rail, not a gem or a corner. The
// source patch is deliberately narrow across the rail. All four patches
// retain their actual gold relief and shadow; there is no generated colour.
export function chooseRailPatch(p,w,h,side){
 const horizontal=side===0||side===2;
 const length=horizontal?w:h,depth=horizontal?h:w;
 const thickness=Math.max(2,Math.round(Math.min(w,h)*.010));
 const span=Math.max(4,Math.round(length*.035));
 const search=Math.max(3,Math.round(depth*.12));
 const first=new Int32Array(length).fill(-1);
 for(let t=0;t<length;t++)for(let d=0;d<search;d++){
  if(gold(p,sideIndex(side,t,d,w,h))){first[t]=d;break;}
 }
 let best=null;
 const stride=Math.max(1,Math.round(span/4));
 for(let t=Math.round(length*.09);t+span<length*.91;t+=stride){
  let score=0,mean=0,valid=0,rough=0,last=-1;
  for(let j=t;j<t+span;j++){
   const d=first[j];
   if(d<0){score-=thickness*8;continue;}
   mean+=d;valid++;
   if(last>=0)rough+=Math.abs(d-last);
   last=d;
   for(let q=0;q<thickness;q++){
    const i=sideIndex(side,j,d+q,w,h);
    score+=gold(p,i)?3:warm(p,i)?1:ruby(p,i)?-9:-2;
   }
  }
  if(!valid)continue;
  score-=rough*4;
  const candidate={start:t,length:span,depth:Math.round(mean/valid),thickness,score};
  if(!best||score>best.score)best=candidate;
 }
 // Fall back to a real gold pixel, not an invented colour, on very small
 // or unusual masters. The original central content is still protected.
 if(!best){
  const t=first.findIndex(v=>v>=0);
  best={start:Math.max(0,t),length:1,depth:t<0?0:first[t],thickness:1,score:0};
 }
 return {...best,first};
}
function patchPixel(p,w,h,side,patch,t,fraction,out,i){
 // Mirror-repeat only the short undecorated source strip along the rail.
 // This changes no original gem or ornament and avoids repeating diamonds.
 const span=patch.length,period=Math.max(1,2*span-2);
 const k=((Math.floor(t)%period)+period)%period;
 const pos=patch.start+(k<span?k:period-k);
 const d0=patch.first[pos]>=0?patch.first[pos]:patch.depth;
 let d=d0+Math.round(clamp(fraction,0,1)*(patch.thickness-1));
 let src=sideIndex(side,pos,d,w,h);
 // Do not copy red jewels or lava into the extension, even if a source
 // patch is imperfect. Choose the nearest actual metallic source pixel.
 if(!warm(p,src)){
  for(let delta=0;delta<patch.thickness;delta++){
   const q=sideIndex(side,pos,d0+delta,w,h);
   if(gold(p,q)){src=q;break;}
  }
 }
 out[i]=p[src];out[i+1]=p[src+1];out[i+2]=p[src+2];out[i+3]=255;
}
export function exteriorAlpha(p,w,h){
 const cx=(w-1)/2,cy=(h-1)/2,a=w-1,b=h-1;
 const trace=traceOuterRail(p,w,h),len=trace.length;
 const patches=[0,1,2,3].map(side=>chooseRailPatch(p,w,h,side));
 const result=new Uint8ClampedArray(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const dx=x-cx,dy=y-cy,t=Math.max(Math.abs(dx)/cx,Math.abs(dy)/cy);
  if(t<=SEARCH)continue;
  const ex=clamp(cx+dx/t,0,a),ey=clamp(cy+dy/t,0,b);
  let k,side,along;
  if(Math.abs(dy)/cy>=Math.abs(dx)/cx){
   side=dy<0?0:2;along=x;k=dy<0?ex:a+b+(a-ex);
  }else{
   side=dx>0?1:3;along=y;k=dx>0?a+ey:2*a+b+(b-ey);
  }
  const k0=Math.floor(k)%len,k1=(k0+1)%len;
  const edge=trace[k0]+(trace[k1]-trace[k0])*(k-Math.floor(k));
  const i=4*(y*w+x);
  // Crucial: no resampling at all on the original engraving or inside it.
  // A one-pixel guard preserves antialiased tips and the ruby outline.
  const guard=1/Math.max(Math.abs(ex-cx),Math.abs(ey-cy));
  if(t<=edge+guard||gold(p,i))continue;
  const fraction=1-clamp((t-edge)/Math.max(1e-6,1-edge),0,1);
  patchPixel(p,w,h,side,patches[side],along,fraction,result,i);
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
