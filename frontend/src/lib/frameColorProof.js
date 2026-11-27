// Revision 21: experimental ARMOR master metal mask. No editor/export changes.
import {getFrontExteriorMask,frontMaskSource} from "./frontExterior";
import {restoredFrontMaster} from "./frontCategoryLayouts";
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
function hsv(r,g,b){
 const v=Math.max(r,g,b),m=Math.min(r,g,b),d=v-m;
 let h=0;
 if(d)h=60*(v===r?(g-b)/d:v===g?2+(b-r)/d:4+(r-g)/d);
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
// The inner edge is the engraved dark contour, not a rectangular band of parchment.
// All traces are calculated from the original art alone, with fixed armor-specific bounds.
export function traceArmorMetal(p,w,h,delta=0){
 const dark=(x,y)=>{const i=4*(clamp(y,0,h-1)*w+clamp(x,0,w-1));return Math.max(p[i],p[i+1],p[i+2])<112;};
 const side=(y,left)=>{
  for(let d=Math.round(w*.078);d>=Math.round(w*.008);d--){
   const x=left?d:w-1-d;
   if(dark(x,y)&&dark(x+(left?1:-1),y))return d;
  }
  return Math.round(w*.035);
 };
 const line=(x,from,to)=>{
  const a=Math.round(from*h),b=Math.round(to*h),step=a<b?1:-1;
  for(let y=a;step*(y-b)<0;y+=step)if(dark(x,y)&&dark(x,y+step))return y;
  return b;
 };
 const sides=Array.from({length:h},(_,y)=>[side(y,true),side(y,false)]);
 const bands=Array.from({length:w},(_,x)=>({
  top:line(x,.045,.005),
  title:[line(x,.126,.155),line(x,.179,.155)],
  art:[line(x,.409,.44),line(x,.473,.44)],
  stats:[line(x,.524,.548),line(x,.576,.548)],
  bottom:line(x,.919+delta,.955+delta)
 }));
 const centers=[];
 for(const x of [.04,.96])for(const y of [.026,.157,.339,.548,.951])centers.push([x,y>.9?y+delta:y]);
 centers.push([.5,.026],[.5,.153],[.5,.445],[.5,.55],[.5,.951+delta],[.333,.454],[.666,.454],[.333,.549],[.666,.549]);
 return (x,y)=>{
  const a=x/w,b=y/h,t=bands[x];
  // Protect medallions and complete diamond cores, including white glints.
  if(b<.175&&((a>.018&&a<.305)||(a>.695&&a<.982)))return false;
  if(centers.some(([cx,cy])=>Math.abs(a-cx)/.023+Math.abs(b-cy)/.017<1.05))return false;
  if(x<=sides[y][0]||w-1-x<=sides[y][1])return true;
  if(b<.045&&a>.30&&a<.70)return y<=t.top;
  if(b>.135&&b<.166&&a>.25&&a<.75)return y>=t.title[0]&&y<=t.title[1];
  if(b>.410&&b<.474)return y>=t.art[0]&&y<=t.art[1];
  if(b>.524&&b<.577)return y>=t.stats[0]&&y<=t.stats[1];
  if(b>.919+delta)return y>=t.bottom;
  return b>.455&&b<.54&&(Math.abs(a-.333)<.009||Math.abs(a-.666)<.009);
 };
}
export function isMetalGold(r,g,b){
 const [h,s,v]=hsv(r,g,b);
 return h>=20&&h<=85&&s>=.12&&v>=56;
}
export function tintArmorMetal(p,master,w,h,target,delta=0){
 const mask=traceArmorMetal(master,w,h,delta);
 let changed=0;
 // Actual reverse metal median (~181/255); preserve relief but suppress neon highlights.
 const valueScale=clamp(target.v/255,.55,.82);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  if(!mask(x,y))continue;
  const i=4*(y*w+x),[r,g,b]=[p[i],p[i+1],p[i+2]];
  if(!isMetalGold(r,g,b)||!isMetalGold(master[i],master[i+1],master[i+2]))continue;
  const [a,s,v]=hsv(r,g,b);
  // Red/ruby pixels never pass the gold selection. Cream paper additionally
  // remains outside the traced contour; faint yellow bevels retain the old tone.
  const hue=clamp(target.h+(a-45)*.32,20,58);
  const sat=clamp(s*.86+.14,.40,.83);
  const col=rgb(hue,sat,v*valueScale);
  for(let q=0;q<3;q++)p[i+q]=col[q];
  changed++;
 }
 return changed;
}
function load(src){
 return new Promise((resolve,reject)=>{
  const im=new Image();im.onload=()=>resolve(im);im.onerror=()=>reject(new Error("Master armatura non disponibile"));im.src=src;
  if(im.complete&&im.naturalWidth)resolve(im);
 });
}
export async function createFrameColorProof(front,back){
 const canvas=document.createElement("canvas");canvas.width=front.width;canvas.height=front.height;
 const ctx=canvas.getContext("2d");ctx.drawImage(front,0,0);
 const bp=back.getContext("2d").getImageData(0,0,back.width,back.height);
 const target=sampleBackGold(bp.data,back.width,back.height);
 if(!target)throw new Error("Campione oro del retro non disponibile");
 const spec=frontMaskSource("armor"),mask=await getFrontExteriorMask("armor");
 const original=await load(mask?.frameBackground||restoredFrontMaster(spec.src));
 const template=document.createElement("canvas");template.width=canvas.width;template.height=canvas.height;
 const t=template.getContext("2d");t.imageSmoothingQuality="high";t.drawImage(original,0,0,template.width,template.height);
 // Include the original synthetic trim only where it already exists.
 if(mask)t.drawImage(mask,0,0,template.width,template.height);
 const pixels=ctx.getImageData(0,0,canvas.width,canvas.height);
 const master=t.getImageData(0,0,template.width,template.height);
 const delta=(mask?.frameMeasurements?.delta||0)/(mask?.frameMeasurements?.height||canvas.height);
 const changed=tintArmorMetal(pixels.data,master.data,canvas.width,canvas.height,target,delta);
 ctx.putImageData(pixels,0,0);
 return {canvas,changed,color:"rgb("+rgb(target.h,target.s,target.v).join(",")+")"};
}
