import { buildFrontBlueprint } from "./cardFrontBlueprint";
import { fitClassDescription } from "./classDescriptionFit";
import { CATEGORY_FRONT_LAYOUTS } from "./frontCategoryLayouts";

const loadImage = (src) => new Promise((resolve, reject) => {
 if (!src) { resolve(null); return; }
 const img = new Image();
 img.onload = () => resolve(img);
 img.onerror = () => reject(new Error("Asset carta non disponibile: "+src));
 img.src = src;
 if (img.complete && img.naturalWidth > 0) resolve(img);
});
const linesFor = (ctx, value, width) => {
 const words = String(value||"").trim().split(/\s+/).filter(Boolean);
 const result=[];let line="";
 for(const word of words){
  const next=line?line+" "+word:word;
  if(line&&ctx.measureText(next).width>width){result.push(line);line=word;}
  else line=next;
 }
 if(line)result.push(line);return result;
};
const fittedCenter = (ctx,text,cx,y,maxWidth,initial=10) => {
 if(!text)return;
 let sz=initial;
 while(sz>7){ctx.font="700 "+sz+"px Georgia,serif";
  if(ctx.measureText(String(text)).width<=maxWidth)break;
  sz-=.5;
 }
 ctx.textAlign="center";ctx.fillText(String(text),cx,y,maxWidth);
};
const roundRect = (ctx,x,y,w,h,r) => {
 ctx.beginPath();ctx.moveTo(x+r,y);ctx.lineTo(x+w-r,y);
 ctx.quadraticCurveTo(x+w,y,x+w,y+r);ctx.lineTo(x+w,y+h-r);
 ctx.quadraticCurveTo(x+w,y+h,x+w-r,y+h);ctx.lineTo(x+r,y+h);
 ctx.quadraticCurveTo(x,y+h,x,y+h-r);ctx.lineTo(x,y+r);
 ctx.quadraticCurveTo(x,y,x+r,y);ctx.closePath();
};
const cropCover = (ctx,img,x,y,w,h) => {
 const scale=Math.max(w/img.naturalWidth,h/img.naturalHeight);
 const srcW=w/scale,srcH=h/scale;
 ctx.drawImage(img,(img.naturalWidth-srcW)/2,(img.naturalHeight-srcH)/2,srcW,srcH,x,y,w,h);
};

// A4, PNG and the live card use the SAME original user JPG: one background.
export async function renderUserOriginalClassCanvas(element,card,size={width:340,height:476,scale:3}){
 const {width,height,scale}=size;
 const canvas=document.createElement("canvas");canvas.width=width*scale;canvas.height=height*scale;
 const ctx=canvas.getContext("2d");ctx.scale(scale,scale);
 if(document.fonts?.ready)await document.fonts.ready;
 const data=buildFrontBlueprint(card);
 const master=await loadImage(CATEGORY_FRONT_LAYOUTS.class.master);
 ctx.drawImage(master,0,0,width,height);
 ctx.save();ctx.scale(width/340,height/476);
 const artNode=element?.querySelector(".tf-class-user-picture img");
 if(artNode){
  const art=artNode.complete&&artNode.naturalWidth>0?artNode:
   await loadImage(artNode.currentSrc||artNode.src).catch(()=>null);
  if(art?.naturalWidth){
   ctx.save();roundRect(ctx,14,89,312,133,12);ctx.clip();
   cropCover(ctx,art,14,89,312,133);ctx.restore();
  }
 }
 const emblem=data.emblem;
 if(emblem){
  const img=await loadImage(emblem.src).catch(()=>null);
  if(img?.naturalWidth){
   const isAtlas=emblem.sprite==="core"||emblem.sprite==="race";
   const sx=isAtlas?(emblem.col||0)*emblem.cell:0;
   const sy=isAtlas?(emblem.row||0)*emblem.cell:0;
   const sw=isAtlas?Math.min(emblem.cell,img.naturalWidth-sx):img.naturalWidth;
   const sh=isAtlas?Math.min(emblem.cell,img.naturalHeight-sy):img.naturalHeight;
   if(sw>0&&sh>0){
    ctx.save();ctx.beginPath();ctx.arc(48.5,48,29,0,Math.PI*2);ctx.clip();
    ctx.drawImage(img,sx,sy,sw,sh,19.5,19,58,58);ctx.restore();
   }
  }
 }
 ctx.fillStyle="#2b190f";
 if(String(card.name||"").trim()){
  fittedCenter(ctx,card.name,170,43,158,22);
  ctx.font="400 10px Georgia,serif";ctx.textAlign="center";
  ctx.fillText("Classe",170,61,158);
 }
 const labels=["Abilità primaria","Tiri salvezza","Competenze"];
 const cells=[{cx:65,w:99},{cx:170,w:98},{cx:276,w:98}];
 labels.forEach((label,i)=>{
  const item=data.highlights.find(entry=>entry.label===label)||{value:""};
  const box=cells[i];ctx.fillStyle="#2f1a0e";
  if(String(card.name||"").trim())fittedCenter(ctx,label,box.cx,246,box.w,10);
  if(item.value){
   ctx.font="700 "+(i===2?8.3:9.4)+"px Georgia,serif";
   linesFor(ctx,item.value,box.w-12).slice(0,4).forEach((line,j)=>
    fittedCenter(ctx,line,box.cx,264+j*10.8,box.w-12,i===2?8.3:9.4));
  }
 });
 if(data.fullDescription){
  const w=218,lh=12.3,h=116;
  ctx.font="400 10px Spectral,Georgia,serif";
  const excerpt=fitClassDescription(data.fullDescription,text=>
   linesFor(ctx,text,w).length*lh<=h);
  ctx.fillStyle="#2b1c12";ctx.textAlign="left";
  linesFor(ctx,excerpt,w).forEach((line,i)=>{
   if(i*lh<h)ctx.fillText(line,22,319+i*lh,w);
  });
 }
 if(data.dice&&data.classDieAsset){
  const die=await loadImage(data.classDieAsset).catch(()=>null);
  if(die?.naturalWidth){ctx.save();ctx.beginPath();ctx.arc(285,362,34,0,Math.PI*2);
   ctx.clip();ctx.drawImage(die,249,326,72,72);ctx.restore();}
 }
 const qr=element?.querySelector("[data-card-qr] canvas");
 if(card.id&&qr){ctx.fillStyle="#fff";ctx.fillRect(292,420,21,21);ctx.drawImage(qr,294,422,17,17);}
 ctx.restore();
 canvas.artworkDrawn=Boolean(artNode?.naturalWidth>0);
 return canvas;
}
