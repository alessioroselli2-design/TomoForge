// Read-only colour experiment for the Cotta di Maglia preview.
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
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
export function isGold(r,g,b){
 const [h,s,v]=hsv(r,g,b);
 return h>=26&&h<=59&&s>=.38&&v>=72;
}
export function isOrnamentRegion(x,y){
 // Entire top medallions, including their projecting jewels, stay unchanged.
 if(y<.20&&((x>.025&&x<.305)||(x>.695&&x<.975)))return false;
 // Restrict to external rails: never the inner illustration, title,
 // internal panels, engraved text, or lower QR/die.
 return x<.083||x>.917||y<.055||y>.925;
}
const median=xs=>{xs.sort((a,b)=>a-b);return xs[Math.floor(xs.length/2)];};
export function sampleRail(p,w,h){
 const hs=[],ss=[],vs=[];
 for(let y=Math.floor(h*.22);y<h*.79;y+=3){
  for(let x=0;x<w;x+=2){
   const nx=x/w;
   if(nx>.083&&nx<.917)continue;
   const i=4*(y*w+x),r=p[i],g=p[i+1],b=p[i+2];
   if(!isGold(r,g,b))continue;
   const [a,s,v]=hsv(r,g,b);hs.push(a);ss.push(s);vs.push(v);
  }
 }
 if(!hs.length)return null;
 return {h:median(hs),s:median(ss),v:median(vs)};
}
export function tintGoldRailPixels(p,w,h,source,target){
 let changed=0;
 const shift=clamp(target.h-source.h,-18,18);
 const brightness=clamp(target.v/source.v,.55,1);
 const saturation=clamp(target.s/source.s,.85,1.15);
 // Protect ruby cores, including a short antialias fringe. This mask is
 // computed before any colour changes and never touches the original buffer.
 const ruby=new Uint8Array(w*h);
 for(let k=0;k<ruby.length;k++){
  const i=4*k,[r,g,b]=[p[i],p[i+1],p[i+2]];
  const [a,s,v]=hsv(r,g,b);
  if((a<20||a>340)&&s>.42&&v>65)ruby[k]=1;
 }
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  if(!isOrnamentRegion(x/w,y/h))continue;
  const k=y*w+x,i=k*4,r=p[i],g=p[i+1],b=p[i+2];
  if(!isGold(r,g,b)||ruby[k])continue;
  let protectedPixel=false;
  for(let dy=-1;dy<=1&&!protectedPixel;dy++)for(let dx=-1;dx<=1;dx++){
   if(x+dx>=0&&x+dx<w&&y+dy>=0&&y+dy<h&&ruby[(y+dy)*w+x+dx]){protectedPixel=true;break;}
  }
  if(protectedPixel)continue;
  const [a,s,v]=hsv(r,g,b);
  // Map the metal towards the sampled bronze while retaining tonal relief.
  const weight=clamp((a-26)/5,0,1)*clamp((59-a)/5,0,1)*clamp((s-.38)/.12,0,1);
  const out=rgb(clamp(a+shift,0,359),clamp(s*saturation,0,1),v*brightness);
  for(let q=0;q<3;q++)p[i+q]=Math.round(p[i+q]+(out[q]-p[i+q])*weight);
  if(weight>0)changed++;
 }
 return changed;
}
export function createFrameColorProof(front,back){
 const canvas=document.createElement("canvas");canvas.width=front.width;canvas.height=front.height;
 const ctx=canvas.getContext("2d");ctx.drawImage(front,0,0);
 const bp=back.getContext("2d").getImageData(0,0,back.width,back.height);
 const fp=ctx.getImageData(0,0,canvas.width,canvas.height);
 const source=sampleRail(fp.data,canvas.width,canvas.height);
 const target=sampleRail(bp.data,back.width,back.height);
 if(!source||!target)throw new Error("Campione oro della cornice non disponibile");
 const changed=tintGoldRailPixels(fp.data,canvas.width,canvas.height,source,target);
 ctx.putImageData(fp,0,0);
 const color=rgb(target.h,target.s,target.v);
 return {canvas,changed,color:"rgb("+color.join(",")+")"};
}
