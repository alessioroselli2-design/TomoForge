// Revision 22: comparison-only mask extracted from the original armor artwork.
// The six connected parchment areas, both medallions and ruby cores are
// explicitly protected. No rectangular tint bands or changes to production.
import {getFrontExteriorMask,frontMaskSource,bottomRailPlan} from "./frontExterior";
import {restoredFrontMaster} from "./frontCategoryLayouts";
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const smooth=(a,lo,hi)=>{const t=clamp((a-lo)/(hi-lo),0,1);return t*t*(3-2*t);};
function hsv(r,g,b){
 const v=Math.max(r,g,b),m=Math.min(r,g,b),d=v-m;
 let h=0;if(d)h=60*(v===r?(g-b)/d:v===g?2+(b-r)/d:4+(r-g)/d);
 return [(h+360)%360,v?d/v:0,v];
}
function rgb(h,s,v){
 const c=v*s,x=c*(1-Math.abs((h/60)%2-1)),m=v-c;
 return [[c,x,0],[x,c,0],[0,c,x],[0,x,c],[x,0,c],[c,0,x]][Math.floor(h/60)%6].map(n=>Math.round(n+m));
}
const median=a=>{a.sort((x,y)=>x-y);return a[Math.floor(a.length/2)];};
export function sampleBackGold(p,w,h){
 const hs=[],ss=[],vs=[];
 for(let y=Math.floor(h*.22);y<h*.79;y+=3)for(let x=0;x<w;x+=2){
  if(x>w*.083&&x<w*.917)continue;
  const i=4*(y*w+x),[a,s,v]=hsv(p[i],p[i+1],p[i+2]);
  if(a<23||a>58||s<.38||v<72)continue;
  hs.push(a);ss.push(s);vs.push(v);
 }
 return hs.length?{h:median(hs),s:median(ss),v:median(vs)}:null;
}
function goldWeight(r,g,b){
 const [a,s,v]=hsv(r,g,b);
 return smooth(a,18,30)*(1-smooth(a,78,93))*smooth(v/255,.12,.24)*smooth(s,.035,.15);
}
export function tintArmorMetal(p,master,protection,exterior,target){
 let changed=0;
 const valueScale=clamp(target.v/255,.55,.82);
 for(let i=0;i<p.length;i+=4){
  // The bitmap is white in the six connected parchment areas and on the
  // complete ruby cores. Interpolated gray pixels provide a soft edge.
  const paper=protection[i]/255;
  // The synthetic thin trim is the only part not contained in the master.
  const trim=exterior?.[i+3]===255;
  if(paper>.015&&!trim)continue;
  const [r,g,b]=[p[i],p[i+1],p[i+2]], [a,s,v]=hsv(r,g,b);
  // No red or magenta pixels, neutral shadows, or user content.
  const weight=goldWeight(r,g,b)*goldWeight(master[i],master[i+1],master[i+2]);
  if(weight<=0)continue;
  const hue=clamp(target.h+(a-45)*.26,18,58);
  const sat=clamp(s*.72+.16,.32,.82);
  const col=rgb(hue,sat,v*valueScale);
  for(let q=0;q<3;q++)p[i+q]=Math.round(p[i+q]+(col[q]-p[i+q])*weight);
  changed++;
 }
 return changed;
}
function load(src){
 return new Promise((resolve,reject)=>{
  const im=new Image();im.onload=()=>resolve(im);im.onerror=()=>reject(new Error("Grafica di prova non disponibile: "+src));im.src=src;
  if(im.complete&&im.naturalWidth)resolve(im);
 });
}
function layer(w,h,im){
 const c=document.createElement("canvas");c.width=w;c.height=h;
 const ctx=c.getContext("2d");ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality="high";
 if(im)ctx.drawImage(im,0,0,w,h);
 return c;
}
export async function createFrameColorProof(front,back){
 const w=front.width,h=front.height,canvas=layer(w,h,front),ctx=canvas.getContext("2d");
 const bp=back.getContext("2d").getImageData(0,0,back.width,back.height);
 const target=sampleBackGold(bp.data,back.width,back.height);
 if(!target)throw new Error("Campione oro del retro non disponibile");
 const spec=frontMaskSource("armor"),mask=await getFrontExteriorMask("armor");
 const [original,protectionImage]=await Promise.all([
  load(mask?.frameBackground||restoredFrontMaster(spec.src)),
  load("/card-art/proofs/armor-paper-protection-v22.png")
 ]);
 const template=layer(w,h,original),t=template.getContext("2d");
 if(mask)t.drawImage(mask,0,0,w,h);
 const raw=layer(w,h,protectionImage);
 let protectedLayer=raw;
 // Reproduce the exact approved lower-rail correction on the mask too.
 if(mask?.frameMeasurements?.delta){
  const originalRaster=layer(w,h,await load(spec.src));
  const fm=mask.frameMeasurements;
  const plan=bottomRailPlan(originalRaster.getContext("2d").getImageData(0,0,w,h).data,w,h,fm.before,fm.reference);
  if(plan){
   const {y,band,delta}=plan,rest=h-y-band-delta;
   protectedLayer=layer(w,h,raw);
   const pc=protectedLayer.getContext("2d");
   pc.drawImage(raw,0,y,w,band,0,y,w,band+delta);
   pc.drawImage(raw,0,y+band,w,rest,0,y+band+delta,w,rest);
  }
 }
 const pixels=ctx.getImageData(0,0,w,h),master=t.getImageData(0,0,w,h);
 const protection=protectedLayer.getContext("2d").getImageData(0,0,w,h).data;
 const exterior=mask?.getContext("2d").getImageData(0,0,w,h).data;
 const changed=tintArmorMetal(pixels.data,master.data,protection,exterior,target);
 ctx.putImageData(pixels,0,0);
 return {canvas,changed,color:"rgb("+rgb(target.h,target.s,target.v).join(",")+")"};
}
