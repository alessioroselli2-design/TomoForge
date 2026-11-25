// Draw right-medallion text natively: html2canvas can clip flex text on iOS.
import {fitExportHeading} from "./exportHeading";
const SELECTOR=".tf-category-badge,.tf-race-size,.tf-feature-level,.tf-spell-level";
const clean=v=>String(v??"").trim().replace(/\s+/g," ");
export function captureExportBadge(clone){
 const badge=clone.querySelector?.(SELECTOR);
 if(!badge)return null;
 const root=clone.getBoundingClientRect(),b=badge.getBoundingClientRect();
 if(!root.width||!root.height||!b.width||!b.height)return null;
 const read=el=>{if(!el)return null;const css=getComputedStyle(el);return {text:clean(el.getAttribute("title")||el.textContent),family:css.fontFamily||"Georgia, serif",weight:css.fontWeight||"700",color:css.color||"#fff1d2"};};
 const level=badge.matches(".tf-feature-level,.tf-spell-level");
 const value=read(badge.querySelector("strong")),label=read(badge.querySelector("span"));
 if(!value?.text)return null;
 badge.style.visibility="hidden";
 return {x:(b.left-root.left+b.width/2)/root.width,y:(b.top-root.top+b.height/2)/root.height,w:b.width/root.width,h:b.height/root.height,level,value,label};
}
export function paintExportBadge(canvas,badge){
 if(!badge)return;
 const ctx=canvas.getContext("2d"),scale=canvas.width/340;
 const diameter=Math.min(badge.w*canvas.width,badge.h*canvas.height);
 const w=diameter*.72,h=diameter*.62;
 const x=badge.x*canvas.width,y=badge.y*canvas.height-2*scale;
 ctx.save();ctx.setTransform(1,0,0,1,0,0);ctx.textAlign="center";ctx.textBaseline="middle";
 const hasLabel=!!badge.label?.text;
 const gap=hasLabel?2*scale:0;
 const label=hasLabel?fitExportHeading(ctx,badge.label.text,w,Math.min(h*.32,11*scale),badge.label.family,badge.label.weight,8*scale,1):null;
 const value=fitExportHeading(ctx,badge.value.text,w,h-(label?label.lineHeight+gap:0),badge.value.family,badge.value.weight,(badge.level?23:14)*scale,badge.level?1:2);
 const total=value.lines.length*value.lineHeight+(label?label.lineHeight+gap:0);
 let top=y-total/2;
 const draw=(entry,fit)=>{ctx.font=entry.weight+" "+fit.size+"px "+entry.family;ctx.fillStyle=entry.color;for(const line of fit.lines){ctx.fillText(line,x,top+fit.lineHeight/2,w);top+=fit.lineHeight;}};
 if(label&&!badge.level){draw(badge.label,label);top+=gap;}
 draw(badge.value,value);
 if(label&&badge.level){top+=gap;draw(badge.label,label);}
 ctx.restore();
 canvas.exportBadge={value:badge.value.text,label:badge.label?.text||"",lines:value.lines};
}
