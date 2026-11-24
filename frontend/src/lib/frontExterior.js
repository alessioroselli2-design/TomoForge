import {categoryFrontLayout,FRONT_OUTER_MASTER} from "./frontCategoryLayouts";
import {CATEGORY_MASTERS} from "./categoryCardView";
import {frontMasterSlices} from "./cardPrintGeometry";

// Determine the outside of the engraved gold frame from the MASTER, never
// from user art, text, jewels or card data. No extra margin or rescaling.
// These peripheral search bands are deliberately limited so the parchment
// and illustration window cannot be recoloured. The original master remains.
const W=1020,H=1428;
const gold=(p,i)=>p[i]>105 && p[i+1]>75 && p[i+1]>=p[i]*.55 && p[i+2]<p[i+1]*.88;
// Use actual warm metallic samples from the original perimeter. The palette
// is shared by all four edges: no row/column extrapolation or streaking.
export function framePalette(p,indices) {
 const samples=[];
 for(const i of indices)if(gold(p,i))samples.push([p[i],p[i+1],p[i+2]]);
 samples.sort((a,b)=>(a[0]*.2126+a[1]*.7152+a[2]*.0722)-(b[0]*.2126+b[1]*.7152+b[2]*.0722));
 if(!samples.length)return {shadow:[100,58,22],mid:[157,102,45],light:[192,139,67]};
 const q=(v)=>samples[Math.round((samples.length-1)*v)];
 return {shadow:q(.10),mid:q(.38),light:q(.68)};
}
const mix=(a,b,t)=>a.map((v,i)=>v+(b[i]-v)*t);
function hash(x,y){
 let n=Math.imul(x+101,374761393)^Math.imul(y+103,668265263);
 n=Math.imul(n^(n>>>13),1274126177);
 return ((n^(n>>>16))>>>0)/4294967295;
}
function noise(x,y,size){
 const u=x/size,v=y/size,ix=Math.floor(u),iy=Math.floor(v);
 const smooth=t=>t*t*(3-2*t);
 const a=smooth(u-ix),b=smooth(v-iy);
 const p=hash(ix,iy)*(1-a)+hash(ix+1,iy)*a;
 const q=hash(ix,iy+1)*(1-a)+hash(ix+1,iy+1)*a;
 return p*(1-b)+q*b;
}
// Fine, isotropic antique-metal patina. The mottling is deliberately subtle
// and two-dimensional, not copied down columns. A narrow warm highlight and
// shadow at the edge suggest the existing gilded relief, without another rail.
export function patinaPixel(palette,x,y,w,h,distance){
 const scale=w/1020;
 const n=.55*noise(x,y,22*scale)+.30*noise(x,y,7*scale)+.15*noise(x,y,2.6*scale);
 const tone=mix(palette.shadow,palette.mid,.68+.28*n);
 const detail=mix(tone,palette.light,.10+.19*n);
 const outer=Math.min(x,y,w-1-x,h-1-y)/scale;
 const edgeShade=.78+.22*Math.min(1,outer/4.5);
 const near=.12*Math.exp(-Math.max(0,distance)/Math.max(1,3*scale));
 const shade=edgeShade*(.97+.10*(n-.5));
 return mix(detail,palette.shadow,near).map(v=>Math.max(0,Math.min(255,Math.round(v*shade))));
}
export function exteriorAlpha(p,w,h) {
 const left=new Int32Array(h),right=new Int32Array(h),
  top=new Int32Array(w),bottom=new Int32Array(w);
 const side=Math.ceil(w*.075),upper=Math.ceil(h*.055),lower=Math.ceil(h*.14);
 const isGold=(x,y)=>gold(p,4*(y*w+x));
 for(let y=0;y<h;y++){
   left[y]=Math.floor(w*.008);right[y]=w-1-Math.floor(w*.008);
   for(let x=0;x<side;x++)if(isGold(x,y)){left[y]=x;break;}
   for(let x=w-1;x>=w-side;x--)if(isGold(x,y)){right[y]=x;break;}
 }
 for(let x=0;x<w;x++){
   top[x]=Math.floor(h*.003);bottom[x]=h-1-Math.floor(h*.003);
   for(let y=0;y<upper;y++)if(isGold(x,y)){top[x]=y;break;}
   for(let y=h-1;y>=h-lower;y--)if(isGold(x,y)){bottom[x]=y;break;}
 }
 const indices=[];
 // Sample short strips inside the already detected original gold contour.
 const dx=Math.max(2,Math.round(w*.009)),dy=Math.max(2,Math.round(h*.009));
 for(let y=0;y<h;y+=2)for(let j=0;j<dx;j++){
  if(left[y]+j<w)indices.push(4*(y*w+left[y]+j));
  if(right[y]-j>=0)indices.push(4*(y*w+right[y]-j));
 }
 for(let x=0;x<w;x+=2)for(let j=0;j<dy;j++){
  if(top[x]+j<h)indices.push(4*((top[x]+j)*w+x));
  if(bottom[x]-j>=0)indices.push(4*((bottom[x]-j)*w+x));
 }
 const palette=framePalette(p,indices);
 const result=new Uint8ClampedArray(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
   const i=4*(y*w+x);
   const distance=Math.max(left[y]-x,x-right[y],top[x]-y,y-bottom[x]);
   if(distance<=0||gold(p,i))continue;
   const rgb=patinaPixel(palette,x,y,w,h,distance);
   result.set([...rgb,255],i);
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
