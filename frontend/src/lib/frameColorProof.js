// Revision 23: a standalone lossless proof master, rendered beneath the normal
// content. The approved assets, production editor and export entrypoints do not
// select this master. Geometry is measured against the original artwork only.
import {getFrontExteriorMask,frontMaskSource,bottomRailPlan} from "./frontExterior";
import {renderArmorMasterProof} from "./cardExport";
export const BRONZE_MASTER_URL="/card-art/proofs/armor-bronze-v23.webp";
const palette=[[0,0,0],[25,14,7],[74,44,20],[161,98,34],[203,133,53],[230,164,80],[250,201,119]];
const knots=[0,30,70,125,180,225,255];
export function bronzeTrimColor(r,g,b){
 const l=.2126*r+.7152*g+.0722*b;
 let j=0;while(j<knots.length-2&&l>knots[j+1])j++;
 const f=(l-knots[j])/(knots[j+1]-knots[j]);
 return palette[j].map((v,q)=>Math.round(v+(palette[j+1][q]-v)*f));
}
function load(src){
 return new Promise((resolve,reject)=>{
  const image=new Image();image.onload=()=>resolve(image);image.onerror=()=>reject(new Error("Master di prova non disponibile"));
  image.src=src;if(image.complete&&image.naturalWidth)resolve(image);
 });
}
function layer(w,h,image){
 const c=document.createElement("canvas");c.width=w;c.height=h;
 const ctx=c.getContext("2d");ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality="high";
 if(image)ctx.drawImage(image,0,0,w,h);
 return c;
}
export async function createFrameColorProof(element,front){
 const w=front.width,h=front.height;
 const [asset,original,mask]=await Promise.all([
  load(BRONZE_MASTER_URL),load(frontMaskSource("armor").src),getFrontExteriorMask("armor")
 ]);
 // Use the already approved bottom-rail plan at exactly the same coordinates
 // as the original master. No colour-based geometry detection on the proof.
 const fm=mask?.frameMeasurements;
 const originalRaster=layer(w,h,original);
 const plan=fm?.delta?bottomRailPlan(originalRaster.getContext("2d").getImageData(0,0,w,h).data,w,h,fm.before,fm.reference):null;
 const source=layer(w*2,h*2,asset);
 let background=source;
 if(plan){
  const {y,band,delta}=Object.fromEntries(Object.entries(plan).map(([k,v])=>[k,v*2]));
  const rest=source.height-y-band-delta;
  background=layer(source.width,source.height,source);
  const b=background.getContext("2d");
  b.drawImage(source,0,y,source.width,band,0,y,source.width,band+delta);
  b.drawImage(source,0,y+band,source.width,rest,0,y+band+delta,source.width,rest);
 }
 const canvas=await renderArmorMasterProof(element,background);
 // Only the pre-existing synthetic trim receives the same metal palette.
 // It is not a filter on the completed card, and its alpha/shape is preserved.
 if(mask){
  const trim=layer(w,h,mask),t=trim.getContext("2d"),pixels=t.getImageData(0,0,w,h);
  for(let i=0;i<pixels.data.length;i+=4){
   if(!pixels.data[i+3])continue;
   const c=bronzeTrimColor(pixels.data[i],pixels.data[i+1],pixels.data[i+2]);
   pixels.data.set(c,i);
  }
  t.putImageData(pixels,0,0);canvas.getContext("2d").drawImage(trim,0,0);
 }
 return {canvas,color:"rgb(203,133,53)"};
}
