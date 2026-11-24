import {categoryFrontLayout,FRONT_OUTER_MASTER} from "./frontCategoryLayouts";
import {CATEGORY_MASTERS} from "./categoryCardView";
import {frontMasterSlices} from "./cardPrintGeometry";

// Determine the outside of the engraved gold frame from the MASTER, never
// from user art, text, jewels or card data. No extra margin or rescaling.
// These peripheral search bands are deliberately limited so the parchment
// and illustration window cannot be recoloured. The original master remains.
const W=1020,H=1428;
const gold=(p,i)=>p[i]>105 && p[i+1]>75 && p[i+1]>=p[i]*.55 && p[i+2]<p[i+1]*.88;
// Pick the dark bronze and gold relief immediately INSIDE the outer rail,
// rather than a single colour sampled from the entire master. Average a
// small neighbourhood along the rail to avoid repeating sharp streaks.
export function localRailColors(p,w,h,edge,side) {
 const vertical=side==="left"||side==="right";
 const count=vertical?h:w, depth=vertical?w:h;
 const sign=side==="left"||side==="top"?1:-1;
 const raw=new Float32Array(count*3);
 for(let t=0;t<count;t++){
  let r=0,g=0,b=0,weight=0;
  for(let j=0;j<Math.max(5,Math.round(depth*.012));j++){
   const d=edge[t]+sign*j;
   if(d<0||d>=depth)continue;
   const i=4*(vertical?t*w+d:d*w+t);
   // Keep the warm brown shadows and gold highlights; reject saturated lava,
   // ruby jewels and neutral black pixels.
   if(p[i]<45||p[i+1]<p[i]*.43||p[i+2]>p[i+1]*.93)continue;
   const k=j===0?2:1;
   r+=p[i]*k;g+=p[i+1]*k;b+=p[i+2]*k;weight+=k;
  }
  raw.set(weight?[r/weight,g/weight,b/weight]:[92,56,23],t*3);
 }
 const result=new Float32Array(count*3);
 const radius=Math.max(1,Math.round(count*.006));
 for(let t=0;t<count;t++){
  let sum=[0,0,0],weights=0;
  for(let j=-radius;j<=radius;j++){
   const pos=Math.max(0,Math.min(count-1,t+j));
   const k=radius+1-Math.abs(j);weights+=k;
   for(let q=0;q<3;q++)sum[q]+=raw[pos*3+q]*k;
  }
  for(let q=0;q<3;q++)result[t*3+q]=sum[q]/weights;
 }
 return result;
}

// Subtle warm metallic bevel: the frame's local hue continues outwards,
// with shadow in the outermost area and soft relief, never a flat gold band.
export function railPixel(color,fraction,x,y) {
 const u=Math.max(0,Math.min(1,fraction));
 const shade=.46+.48*Math.pow(1-u,.8)+.12*Math.exp(-Math.pow((u-.72)/.12,2));
 const grain=1+.026*Math.sin(x*1.37+y*.83)+.014*Math.sin(x*.39-y*1.61);
 return color.map(v=>Math.max(0,Math.min(255,Math.round(v*shade*grain))));
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
 const rails=[
  {edge:left,colors:localRailColors(p,w,h,left,"left"),side:"left"},
  {edge:right,colors:localRailColors(p,w,h,right,"right"),side:"right"},
  {edge:top,colors:localRailColors(p,w,h,top,"top"),side:"top"},
  {edge:bottom,colors:localRailColors(p,w,h,bottom,"bottom"),side:"bottom"},
 ];
 const result=new Uint8ClampedArray(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
   const i=4*(y*w+x);
   const distances=[left[y]-x,x-right[y],top[x]-y,y-bottom[x]];
   if(Math.max(...distances)<=0||gold(p,i))continue;
   // Blend adjacent rails smoothly at the corners. Preserve every existing
   // gold pixel and every pixel inside the engraved contour.
   const spans=[left[y],w-1-right[y],top[x],h-1-bottom[x]];
   const t=[y,y,x,x];let rgb=[0,0,0],total=0;
   for(let k=0;k<4;k++){
    if(distances[k]<=0)continue;
    const f=distances[k]/Math.max(1,spans[k]);
    const col=rails[k].colors.subarray(t[k]*3,t[k]*3+3);
    const sample=railPixel(Array.from(col),f,x,y);
    const weight=distances[k];total+=weight;
    for(let q=0;q<3;q++)rgb[q]+=sample[q]*weight;
   }
   for(let q=0;q<3;q++)result[i+q]=Math.round(rgb[q]/total);
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
