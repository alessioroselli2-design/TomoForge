import {categoryFrontLayout,FRONT_OUTER_MASTER} from "./frontCategoryLayouts";
import {CATEGORY_MASTERS} from "./categoryCardView";
import {frontMasterSlices} from "./cardPrintGeometry";

// Determine the outside of the engraved gold frame from the MASTER, never
// from user art, text, jewels or card data. No extra margin or rescaling.
// These peripheral search bands are deliberately limited so the parchment
// and illustration window cannot be recoloured. The original master remains.
const W=1020,H=1428;
const gold=(p,i)=>p[i]>105 && p[i+1]>75 && p[i+1]>=p[i]*.55 && p[i+2]<p[i+1]*.88;
// Sample the actual engraved gold, not the red lava or parchment. The
// lower-middle luminance percentile picks an antique-gold mid-shadow.
// A single sampled tone avoids striped or stretched edge pixels.
export function sampleAntiqueGold(p,indices) {
 const samples=[];
 for(const i of indices)if(gold(p,i))samples.push([p[i],p[i+1],p[i+2]]);
 if(!samples.length)return [151,103,47];
 samples.sort((a,b)=>(.2126*a[0]+.7152*a[1]+.0722*a[2])-(.2126*b[0]+.7152*b[1]+.0722*b[2]));
 return samples[Math.floor((samples.length-1)*.35)];
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
 for(let y=0;y<h;y++){
   indices.push(4*(y*w+left[y]),4*(y*w+right[y]));
 }
 for(let x=0;x<w;x++){
   indices.push(4*(top[x]*w+x),4*(bottom[x]*w+x));
 }
 const [r,g,b]=sampleAntiqueGold(p,indices);
 const result=new Uint8ClampedArray(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
   const i=4*(y*w+x);
   if((x<left[y]||x>right[y]||y<top[x]||y>bottom[x])&&!gold(p,i)){
     result[i]=r;result[i+1]=g;result[i+2]=b;result[i+3]=255;
   }
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
