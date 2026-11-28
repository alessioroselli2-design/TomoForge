import {categoryFrontLayout,FRONT_OUTER_MASTER,restoredFrontMaster} from "./frontCategoryLayouts";
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
export function traceOuterRail(p,w,h,detect=gold){
 const cx=(w-1)/2,cy=(h-1)/2,len=2*(w+h-2);
 const ray=new Float32Array(len);
 for(let k=0;k<len;k++){
  const [ex,ey]=perimeterPoint(k,w,h);
  const dx=ex-cx,dy=ey-cy,steps=Math.max(Math.abs(dx),Math.abs(dy));
  for(let n=0;n<=Math.ceil(steps*(1-SEARCH));n++){
   const t=1-n/steps,x=Math.round(cx+dx*t),y=Math.round(cy+dy*t);
   if(detect(p,4*(y*w+x))){ray[k]=t;break;}
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
// A gold-only ray can fall between the narrow highlights of a sculpted
// ornament. Protect pale metal highlights as well as gold, then use the
// outer envelope of adjacent rays, including the carved dark outline.
// Never derive this boundary from recoloured pixels or dynamic contents.
const ornamentHighlight=(p,i)=>gold(p,i)||
 (p[i]>155&&p[i+1]>115&&p[i]>=p[i+1]*.94&&p[i+2]>p[i+1]*.84)||
 (p[i]>160&&p[i+2]>95&&p[i+2]>p[i+1]*.95);
export function safeExteriorTrace(p,w,h){
 const raw=traceOuterRail(p,w,h,ornamentHighlight),len=raw.length;
 const span=Math.max(2,Math.round(w*.012)),trace=new Float32Array(len);
 for(let k=0;k<len;k++){
  let far=raw[k];
  for(let j=-span;j<=span;j++)far=Math.max(far,raw[(k+j+len)%len]);
  trace[k]=far;
 }
 return trace;
}
export function exteriorAlpha(p,w,h,artwork=p){
 const cx=(w-1)/2,cy=(h-1)/2,a=w-1,b=h-1;
 const trace=safeExteriorTrace(artwork,w,h),railTrace=traceOuterRail(p,w,h),len=trace.length,profile=sampleRailProfile(p,w,h);
 const width=Math.max(2,w*.009),shadow=[44,17,6];
 const result=new Uint8ClampedArray(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const dx=x-cx,dy=y-cy,t=Math.max(Math.abs(dx)/cx,Math.abs(dy)/cy);
  if(t<=SEARCH)continue;
  const ex=clamp(cx+dx/t,0,a),ey=clamp(cy+dy/t,0,b);
  const k=Math.abs(dy)/cy>=Math.abs(dx)/cx?(dy<0?ex:a+b+(a-ex)):(dx>0?a+ey:2*a+b+(b-ey));
  const k0=Math.floor(k)%len,k1=(k0+1)%len;
  const d=roundedTrimDistance(x,y,w,h);
  // Keep the established outer double rail. Beyond it, the dark matte must
  // stay outside the full ornamental silhouette, not just the gold cores.
  const contour=d<width?railTrace:trace;
  const edge=contour[k0]+(contour[k1]-contour[k0])*(k-Math.floor(k));
  const i=4*(y*w+x),step=1/Math.max(Math.abs(ex-cx),Math.abs(ey-cy));
  const guard=d<width?step:Math.max(2,w*.003)*step;
  if(t<=edge+guard||gold(p,i)||ornamentHighlight(artwork,i))continue;
  const z=clamp(d/Math.max(1,width-1),0,1)*(profile.length-1),j=Math.floor(z),frac=z-j;
  const col=profile[j].map((v,q)=>v*(1-frac)+profile[Math.min(j+1,profile.length-1)][q]*frac);
  const blend=d<0?0:clamp(width-d,0,1);
  for(let q=0;q<3;q++)result[i+q]=Math.round(shadow[q]*(1-blend)+col[q]*blend);
  result[i+3]=255;
 }
 return result;
}


// Measure the existing straight engraved rails, not the synthetic trim line.
// Use several central spans, away from the corner and centre jewels. A majority
// vote rejects isolated highlights in the lava outside the original frame.
const railGold=(p,i)=>p[i]>130&&p[i+1]>85&&p[i]-p[i+1]>18&&p[i+2]<p[i+1]*.65;
export function measureFrameRails(p,w,h){
 const scan=(vertical,reverse)=>{
  const length=vertical?h:w, across=vertical?w:h;
  const samples=[];
  for(let j=Math.round(across*.28);j<across*.72;j+=Math.max(1,Math.round(across/200))){
   if(j>across*.43&&j<across*.57)continue;
   samples.push(j);
  }
  for(let d=0;d<Math.round(length*.12);d++){
   const a=reverse?length-1-d:d;
   let hits=0;
   for(const b of samples){const i=4*(vertical?a*w+b:b*w+a);if(railGold(p,i))hits++;}
   if(hits>=samples.length*.36)return d;
  }
  return null;
 };
 return {top:scan(true,false),bottom:scan(true,true),left:scan(false,false),right:scan(false,true)};
}
// Keep the lower ornamental block at original pixel size. Only a narrow
// straight parchment/side-rail strip is lengthened, below the last divider.
export function bottomRailPlan(p,w,h,before,reference){
 if(before.bottom===null||reference.bottom===null)return null;
 let delta=Math.min(Math.round(h*.045),Math.max(0,before.bottom-reference.bottom));
 if(delta<3)return null;
 const rail=h-1-before.bottom;
 // Keep the central diamond's entire tip within the trim.
 let tip=rail;
 for(let y=rail;y<Math.min(h,rail+Math.round(h*.035));y++){
  let n=0;for(let x=Math.round(w*.465);x<w*.535;x++)if(railGold(p,4*(y*w+x)))n++;
  if(n>=3)tip=y;
 }
 delta=Math.min(delta,Math.max(0,h-2-tip));
 if(delta<3)return null;
 const band=Math.max(6,Math.round(h*.009));
 let best=null;
 // Prefer a late blank band so all internal dividers and content stay put.
 for(let y=Math.round(rail-h*.095);y+band<=rail-h*.058;y+=2){
  if(y<0)continue;
  let score=0;
  for(let yy=y;yy<y+band;yy++){
   for(let x=Math.round(w*.16);x<w*.84;x+=4){
    const i=4*(yy*w+x);
    // Penalize gold strokes, red gems, dark rules and non-parchment.
    if(railGold(p,i)||p[i]<165||p[i+1]<120||p[i+2]<85)score+=1;
   }
   for(const x of [Math.round(w*.03),Math.round(w*.97)]){
    const i=4*(yy*w+x);
    if(p[i]>110&&p[i+1]<p[i]*.40)score+=10;
   }
  }
  score+=(rail-y)/h;
  if(!best||score<best.score)best={y,band,delta,score};
 }
 // No suitable blank band: leave the approved master unchanged.
 if(!best||best.score>band*w*.025)return null;
 return {y:best.y,band,delta};
}
function extendBottomMaster(master,plan){
 const w=master.width,h=master.height,{y,band,delta}=plan;
 const output=document.createElement("canvas");output.width=w;output.height=h;
 const ctx=output.getContext("2d");
 ctx.drawImage(master,0,0);
 ctx.drawImage(master,0,y,w,band,0,y,w,band+delta);
 const start=y+band,remaining=h-start-delta;
 ctx.drawImage(master,0,start,w,remaining,0,start+delta,w,remaining);
 return output;
}

export function frontMaskSource(type) {
 const dedicated={spell:"master-incantesimo-5x7-v1.webp",feature:"master-privilegi-5x7.png",race:"master-razze-5x7.png"};
 const asset=dedicated[type]||CATEGORY_MASTERS[type]?.master;
 if(asset)return {src:"/card-art/"+asset,legacy:false,type};
 const normalized=type==="subclass"?"class":type;
 return {src:categoryFrontLayout(normalized).master||FRONT_OUTER_MASTER,legacy:true,type:normalized};
}
const cache=new Map();
export function loadMaster(src){
 return new Promise((resolve,reject)=>{
  const image=new Image();image.onload=()=>resolve(image);image.onerror=()=>reject(new Error("Cornice fronte non disponibile: "+src));
  image.src=src;if(image.complete&&image.naturalWidth)resolve(image);
 });
}
// Transform the HD artwork with the trim-resolution plan measured on the approved
// source. Any colour separation belongs on the master before the same slices.
export function prepareNativeMaster(image, plan, metalLayer=null) {
 const hi=document.createElement("canvas");
 hi.width=2*W;hi.height=2*H;
 const ctx=hi.getContext("2d");
 ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality="high";
 ctx.drawImage(image,0,0,hi.width,hi.height);
 if(metalLayer)ctx.drawImage(metalLayer,0,0);
 return plan?extendBottomMaster(hi,{y:2*plan.y,band:2*plan.band,delta:2*plan.delta}):hi;
}
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
   const before=measureFrameRails(rgba.data,W,H);
   let corrected=master, reference=before, plan=null;
   if(spec.type!=="monster"){
     const monster=await getFrontExteriorMask("monster");
     reference=monster?.frameMeasurements?.after||before;
   }
   // Legacy Monster/Class already move their lower rail via frontMasterSlices.
   // Dedicated masters get a calibrated correction, without modifying assets.
   if(!spec.legacy){
     plan=bottomRailPlan(rgba.data,W,H,before,reference);
     if(plan)corrected=extendBottomMaster(master,plan);
   }
   const correctedPixels=corrected===master?rgba:corrected.getContext("2d").getImageData(0,0,W,H);
   const after=measureFrameRails(correctedPixels.data,W,H);
   // The restored master is the exact artwork being rendered. Trace it
   // after the same approved slices/plan, retaining original rail profile
   // and all existing geometry measurements.
   const restored=await loadMaster(restoredFrontMaster(spec.src));
   const native=prepareNativeMaster(restored,plan);
   const contourCanvas=document.createElement("canvas");contourCanvas.width=W;contourCanvas.height=H;
   const contourCtx=contourCanvas.getContext("2d");
   contourCtx.imageSmoothingEnabled=true;contourCtx.imageSmoothingQuality="high";
   contourCtx.drawImage(native,0,0,W,H);
   if(spec.legacy)frontMasterSlices(spec.type).forEach(s=>contourCtx.drawImage(native,0,s.sourceY*native.height,native.width,s.sourceH*native.height,0,s.y*H,W,s.h*H));
   const contourPixels=contourCtx.getImageData(0,0,W,H).data;
   const mask=document.createElement("canvas");mask.width=W;mask.height=H;
   const out=mask.getContext("2d"),data=out.createImageData(W,H);
   data.data.set(exteriorAlpha(correctedPixels.data,W,H,contourPixels));out.putImageData(data,0,0);
   // Measure and trace the ORIGINAL at the established trim resolution;
   // apply the identical correction to the restored double-resolution source.
   mask.frameBackground=null;
   if(plan)mask.frameBackground=native.toDataURL("image/png");
   mask.bottomPlan=plan;
   mask.frameMeasurements={before,after,reference,delta:plan?.delta||0,width:W,height:H};
   return mask;
 })();
 cache.set(key,pending);
 pending.catch(()=>cache.delete(key));
 return pending;
}
export async function colorFrontExterior(canvas,type,proofTrim=null) {
 const ctx=canvas.getContext("2d");
 // Minimal canvas mocks do not expose pixel APIs; production canvases do.
 if(typeof ctx.getImageData!=="function")return canvas;
 const mask=proofTrim||await getFrontExteriorMask(type);
 if(!mask)throw new Error("Maschera cornice non disponibile");
 ctx.save();ctx.setTransform(1,0,0,1,0,0);
 ctx.globalCompositeOperation="source-over";
 ctx.drawImage(mask,0,0,canvas.width,canvas.height);ctx.restore();
 canvas.frameMeasurements=mask.frameMeasurements;
 return canvas;
}

// html2canvas can resample a CSS background to the small DOM size before
// applying its export scale. Capture only the transparent foreground and draw
// the complete restored master directly at the final canvas resolution.
export async function prepareFrontBackground(clone,type){
 const probe=document.createElement("canvas").getContext("2d");
 if(!probe||typeof probe.getImageData!=="function")return null;
 const mask=await getFrontExteriorMask(type);
 const image=await loadMaster(mask?.frameBackground||restoredFrontMaster(frontMaskSource(type).src));
 clone.style.backgroundImage="none";
 clone.style.backgroundColor="transparent";
 return image;
}
export function paintNativeFrontBackground(canvas,image){
 if(!image)return;
 const ctx=canvas.getContext("2d");
 ctx.save();ctx.setTransform(1,0,0,1,0,0);
 ctx.globalCompositeOperation="destination-over";
 ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality="high";
 ctx.drawImage(image,0,0,canvas.width,canvas.height);
 ctx.restore();
}
