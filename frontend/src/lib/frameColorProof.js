// Experimental comparison only. Never used by the production card renderer.
// Sample the actual printed reverse, then recolour only red ornament pixels.
// Gold, parchment, text, emblems, badges, illustration and dice stay intact.
const clamp=(x,a,b)=>Math.min(b,Math.max(a,x));
function hsv(r,g,b){
 const v=Math.max(r,g,b),m=Math.min(r,g,b),d=v-m;
 let h=0;
 if(d)h=60*(v===r?(g-b)/d:v===g?2+(b-r)/d:4+(r-g)/d);
 return [(h+360)%360,v?d/v:0,v];
}
function rgb(h,s,v){
 const c=v*s,x=c*(1-Math.abs((h/60)%2-1)),m=v-c;
 const k=Math.floor(h/60)%6;
 return [[c,x,0],[x,c,0],[0,c,x],[0,x,c],[x,0,c],[c,0,x]][k].map(n=>Math.round(n+m));
}
export function reverseAccent(p,w,h,silver=false){
 if(silver)return {h:215,s:.12,label:"Argento"};
 const bins=new Float64Array(36),sat=new Float64Array(36);
 // Central artwork, not the common gold edging. Saturated luminous pixels
 // carry the category accent; neutral highlights don't vote.
 for(let y=Math.floor(h*.18);y<h*.82;y+=3)for(let x=Math.floor(w*.18);x<w*.82;x+=3){
  const i=4*(y*w+x),[a,s,v]=hsv(p[i],p[i+1],p[i+2]);
  if(s<.42||v<105)continue;
  const k=Math.floor(a/10),weight=s*s*(v/255)**2;
  bins[k]+=weight;sat[k]+=s*weight;
 }
 let best=0,score=-1;
 for(let k=0;k<36;k++){
  const a=(k+35)%36,b=(k+1)%36;
  const value=bins[k]+.55*(bins[a]+bins[b]);
  if(value>score){score=value;best=k;}
 }
 const hue=score>0?best*10+5:43;
 const s=score>0&&bins[best]>0?clamp(sat[best]/bins[best],.48,.9):.65;
 return {h:hue,s,label:"Tonalità campionata dal retro"};
}
export function isOrnamentRegion(x,y,type){
 // Protect the two upper medallions including their protruding jewels.
 if(y<.18&&((x>.035&&x<.30)||(x>.70&&x<.965)))return false;
 // Main artwork / lava window must not be recoloured, including the
 // shorter legacy character/monster picture. The sample has no user art.
 if(y>=.13&&y<.49&&x>.09&&x<.91)return false;
 // Keep the entire lower dice/QR area unchanged.
 if(y>.56&&y<.94&&x>.72&&x<.92)return false;
 // Outer rail, including corner jewels.
 if(x<.095||x>.905||y<.045||y>.93)return true;
 // Central and column-divider jewels in the approved lower field grid.
 if(y>=.49&&y<.91){
  const columns=[.16,.25,.33,.40,.50,.60,.66,.75,.84];
  return columns.some(c=>Math.abs(c-x)<.024);
 }
 // Title divider between the two medallions.
 return y<.18&&Math.abs(x-.5)<.035;
}
export function tintOrnamentPixels(p,w,h,accent,type){
 let changed=0;
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  if(!isOrnamentRegion(x/w,y/h,type))continue;
  const i=4*(y*w+x),r=p[i],g=p[i+1],b=p[i+2];
  // Select ruby/red details, never yellow gold or cream parchment.
  if(r<55||r-g<20||r-b<15||g/r>.70)continue;
  const [a,s,v]=hsv(r,g,b);
  if(!(a<20||a>340)||s<.35)continue;
  // Preserve shading and highlights; restrained blend avoids neon edges.
  const f=clamp((.70-g/r)/.22,0,1)*.92;
  const [rr,gg,bb]=rgb(accent.h,Math.min(s,accent.s),v);
  p[i]=Math.round(r+(rr-r)*f);p[i+1]=Math.round(g+(gg-g)*f);p[i+2]=Math.round(b+(bb-b)*f);
  changed++;
 }
 return changed;
}
export function createFrameColorProof(front,back,card){
 const canvas=document.createElement("canvas");
 canvas.width=front.width;canvas.height=front.height;
 const ctx=canvas.getContext("2d");ctx.drawImage(front,0,0);
 const backCtx=back.getContext("2d"),backPixels=backCtx.getImageData(0,0,back.width,back.height);
 const accent=reverseAccent(backPixels.data,back.width,back.height,card.type==="character"&&card.back?.variant==="silver");
 const pixels=ctx.getImageData(0,0,canvas.width,canvas.height);
 const changed=tintOrnamentPixels(pixels.data,canvas.width,canvas.height,accent,card.type);
 ctx.putImageData(pixels,0,0);
 return {canvas,accent,changed};
}
