// Paint dynamic text at final print resolution, independently of html2canvas's
// iOS flex/overflow/line-clamp handling. Keep original card geometry.
const clean=value=>String(value??"").trim().replace(/\s+/g," ");
function wrap(ctx,text,width){
 const lines=[];let line="";
 for(const word of clean(text).split(" ").filter(Boolean)){
  const next=line?line+" "+word:word;
  if(ctx.measureText(next).width<=width){line=next;continue;}
  if(line){lines.push(line);line="";}
  if(ctx.measureText(word).width<=width){line=word;continue;}
  for(const letter of word){if(line&&ctx.measureText(line+letter).width>width){lines.push(line);line="";}line+=letter;}
 }
 if(line)lines.push(line);return lines;
}
export function fitBodyText(ctx,text,width,height,family,weight,max,min,maxLines=Infinity){
 const full=clean(text);
 let size=Math.max(1,max),floor=Math.max(1,Math.min(min,max));
 const at=s=>{ctx.font=weight+" "+s+"px "+family;const lines=wrap(ctx,full,width),lineHeight=s*1.2;return {lines,size:s,lineHeight};};
 for(;size>=floor-.001;size-=.25){const fit=at(size);if(fit.lines.length<=maxLines&&fit.lines.length*fit.lineHeight<=height&&fit.lines.every(l=>ctx.measureText(l).width<=width))return fit;}
 const fit=at(floor);const limit=Math.max(0,Math.min(maxLines,Math.floor(height/fit.lineHeight)));if(fit.lines.length<=limit)return fit;
 // Preserve whole lines and explicitly mark unavoidable overflow.
 const lines=fit.lines.slice(0,limit);if(lines.length){let last=lines[lines.length-1];while(last&&ctx.measureText(last+"…").width>width)last=last.slice(0,-1);lines[lines.length-1]=last.trimEnd()+"…";}
 return {...fit,lines};
}
export function captureExportBody(clone,type){
 const root=clone.getBoundingClientRect();if(!root.width||!root.height)return [];
 const result=[];
 const read=(node,box,opts={})=>{
  if(!node||!box)return;const r=box.getBoundingClientRect();if(!r.width||!r.height)return;
  const css=getComputedStyle(node),text=clean(opts.full?node.getAttribute("title")||node.textContent:node.textContent);
  if(!text)return;
  result.push({text,x:(r.left-root.left)/root.width,y:(r.top-root.top)/root.height,w:r.width/root.width,h:r.height/root.height,
   family:css.fontFamily||"Georgia,serif",weight:css.fontWeight||"700",color:css.color||"#29170e",
   max:Math.min(opts.max||12,(parseFloat(css.fontSize)||9)*340/root.width),min:opts.min||5,maxLines:opts.maxLines||3,align:opts.align||"center",slot:opts.slot||null});
  node.style.visibility="hidden";
 };
 if(type==="spell"){
  for(const cell of clone.querySelectorAll(".tf-spell-cell")){
   const copy=cell.querySelector(".tf-spell-cell-copy");if(!copy)continue;
   // Same horizontal bounds as text; never paint over the icon.
   const cr=cell.getBoundingClientRect(),tr=copy.getBoundingClientRect();
   const box={getBoundingClientRect:()=>({left:tr.left,top:cr.top+2,width:tr.width,height:Math.max(0,cr.height-4)})};
   read(copy.querySelector("span"),box,{slot:"label",max:9,min:6,maxLines:2});
   read(copy.querySelector("strong"),box,{slot:"value",max:11,min:5,maxLines:3});
  }
  const desc=clone.querySelector(".tf-spell-description");read(desc?.querySelector("p"),desc,{align:"left",max:10,min:7,maxLines:10});
  const foot=clone.querySelector(".tf-spell-footnote");if(foot){read(foot.querySelector("strong"),foot,{slot:"label",max:10,min:6,maxLines:1});read(foot.querySelector("p"),foot,{slot:"value",max:9,min:5,maxLines:3});}
 }else{
  for(const node of clone.querySelectorAll(".tf-category-stat-value"))read(node,node.parentElement,{full:true,max:9,min:5,maxLines:3});
 }
 return result;
}
export function paintExportBody(canvas,entries){
 if(!entries?.length)return;const ctx=canvas.getContext("2d"),s=canvas.width/340;
 ctx.save();ctx.setTransform(1,0,0,1,0,0);ctx.textBaseline="middle";
 for(const e of entries){
  let x=e.x*canvas.width+2*s,y=e.y*canvas.height,w=e.w*canvas.width-4*s,h=e.h*canvas.height;
  if(e.slot==="label"){h*=.38;}else if(e.slot==="value"){y+=h*.40;h*=.60;}
  y+=s;h-=2*s;if(w<=0||h<=0)continue;
  const fit=fitBodyText(ctx,e.text,w,h,e.family,e.weight,e.max*s,e.min*s,e.maxLines);
  ctx.font=e.weight+" "+fit.size+"px "+e.family;ctx.fillStyle=e.color;ctx.textAlign=e.align;
  const top=e.align==="left"?y:y+(h-fit.lines.length*fit.lineHeight)/2;
  fit.lines.forEach((line,i)=>ctx.fillText(line,e.align==="left"?x:x+w/2,top+(i+.5)*fit.lineHeight,w));
 }
 ctx.restore();
}
