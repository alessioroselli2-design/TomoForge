// html2canvas does not reproduce every flex/align-content/overflow rule on
// iOS. Render the complete heading separately, using the real header bounds
// and fonts. Never copy a clipped React text node when its full title exists.
const HEADERS=".tf-category-heading,.tf-spell-header,.tf-feature-heading,.tf-race-heading";
const SUBTITLES=".tf-category-subtitle,.tf-feature-subtitle,.tf-race-subtitle,p";
const clean=s=>String(s||"").trim().replace(/\s+/g," ");
export function fitExportHeading(ctx,text,width,height,family,weight,maxSize,maxLines=2){
 const full=clean(text);
 if(!full)return {lines:[],size:maxSize,lineHeight:maxSize*1.15};
 const font=size=>{ctx.font=weight+" "+size+"px "+family;};
 const wrap=()=>{
  const lines=[];let current="";
  for(const word of full.split(" ")){
   if(!current){current=word;continue;}
   if(ctx.measureText(current+" "+word).width<=width)current+=" "+word;
   else{lines.push(current);current=word;}
  }
  if(current)lines.push(current);
  return lines;
 };
 // Prefer one readable line; allow two full lines for longer names.
 for(let size=maxSize;size>=Math.min(12,maxSize);size-=.5){
  font(size);if(ctx.measureText(full).width<=width&&size*1.2<=height)
   return {lines:[full],size,lineHeight:size*1.2};
 }
 for(let size=maxSize;size>=1;size-=.25){
  font(size);const lines=wrap(),lineHeight=size*1.2;
  if(lines.length<=maxLines&&lines.length*lineHeight<=height&&lines.every(l=>ctx.measureText(l).width<=width))
   return {lines,size,lineHeight};
 }
 // Even pathological names remain complete instead of becoming an ellipsis.
 font(1);return {lines:[full],size:1,lineHeight:1.2};
}
export function captureExportHeading(clone){
 const header=clone.querySelector?.(HEADERS),title=header?.querySelector("h3"),subtitle=header?.querySelector(SUBTITLES);
 if(!header||!title)return null;
 const root=clone.getBoundingClientRect(),bounds=header.getBoundingClientRect();
 if(!root.width||!root.height||!bounds.width||!bounds.height)return null;
 const read=(el)=>{if(!el)return null;const css=getComputedStyle(el);return {
  text:clean(el.getAttribute("title")||el.textContent),family:css.fontFamily||"Georgia, serif",weight:css.fontWeight||"700",
  color:css.color||"#29170e"};};
 const result={x:(bounds.left-root.left)/root.width,y:(bounds.top-root.top)/root.height,
  w:bounds.width/root.width,h:bounds.height/root.height,title:read(title),subtitle:read(subtitle)};
 // Hide only the original text, preserving the background and header geometry.
 header.style.visibility="hidden";
 return result;
}
export function paintExportHeading(canvas,heading){
 if(!heading)return;
 const ctx=canvas.getContext("2d"),scale=canvas.width/340;
 const x=(heading.x+heading.w/2)*canvas.width,y=heading.y*canvas.height;
 const w=heading.w*canvas.width-8*scale,h=heading.h*canvas.height-4*scale;
 if(w<=0||h<=0)return;
 const hasSub=!!heading.subtitle?.text;
 const gap=hasSub?2*scale:0,subHeight=hasSub?Math.min(h*.27,12*scale):0;
 ctx.save();ctx.setTransform(1,0,0,1,0,0);ctx.textAlign="center";ctx.textBaseline="middle";
 const title=fitExportHeading(ctx,heading.title.text,w,h-subHeight-gap,heading.title.family,heading.title.weight,20*scale,2);
 const sub=hasSub?fitExportHeading(ctx,heading.subtitle.text,w,subHeight,heading.subtitle.family,heading.subtitle.weight,10*scale,1):null;
 const total=title.lines.length*title.lineHeight+(sub?gap+sub.lineHeight:0);
 let top=y+2*scale+(h-total)/2;
 const draw=(entry,layout)=>{ctx.font=entry.weight+" "+layout.size+"px "+entry.family;ctx.fillStyle=entry.color;
  for(const line of layout.lines){ctx.fillText(line,x,top+layout.lineHeight/2,w);top+=layout.lineHeight;}};
 draw(heading.title,title);if(sub){top+=gap;draw(heading.subtitle,sub);}
 ctx.restore();
 canvas.exportHeading={title:heading.title.text,subtitle:heading.subtitle?.text||"",lines:title.lines};
}
