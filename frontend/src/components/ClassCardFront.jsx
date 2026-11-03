import React from "react";
import { QRCodeCanvas } from "qrcode.react";
import { artworkUrl } from "@/lib/api";
import { buildFrontBlueprint } from "@/lib/cardFrontBlueprint";
import { publicDescriptionUrl } from "@/lib/cardDescription";
import { getFrontStatIcon } from "@/lib/frontStatIcons";
import { fitClassDescription } from "@/lib/classDescriptionFit";
import { frontBackground } from "@/lib/frontCategoryLayouts";

// Identical user-approved JPG: all ornamental graphics live in one fixed raster.
export const ClassCardFront = React.forwardRef(({card,exportMode,editorMode,imgUrl},ref)=>{
 const data=buildFrontBlueprint(card);
 const artSrc=imgUrl||(card.artwork_path?artworkUrl(card.artwork_path):"");
 const [artError,setArtError]=React.useState(false);
 const [description,setDescription]=React.useState(data.fullDescription);
 const textRef=React.useRef(null);
 React.useEffect(()=>setArtError(false),[artSrc]);
 React.useLayoutEffect(()=>{
  const node=textRef.current;
  if(!node)return undefined;
  let done=false;
  const update=()=>{
   if(done)return;
   const w=node.clientWidth,h=node.clientHeight;
   if(!w||!h){setDescription(data.fullDescription);return;}
   const style=window.getComputedStyle(node);
   const probe=document.createElement("div");
   Object.assign(probe.style,{position:"fixed",left:"-10000px",top:"-10000px",
    visibility:"hidden",width:w+"px",height:"auto",maxHeight:"none",
    margin:"0",padding:"0",border:"0",boxSizing:"border-box",
    fontFamily:style.fontFamily,fontSize:style.fontSize,lineHeight:style.lineHeight,
    letterSpacing:style.letterSpacing,whiteSpace:"normal",overflowWrap:"normal"});
   document.body.appendChild(probe);
   try {setDescription(fitClassDescription(data.fullDescription,text=>{
    probe.textContent=text;return probe.getBoundingClientRect().height<=h+.5;
   }));}finally{probe.remove();}
  };
  update();
  const observer=typeof ResizeObserver!=="undefined"?new ResizeObserver(update):null;
  observer?.observe(node);
  if(document.fonts?.ready)document.fonts.ready.then(update).catch(()=>{});
  return()=>{done=true;observer?.disconnect();};
 },[data.fullDescription]);
 const emblem=data.emblem;
 const name=String(card.name||"").trim();
 const link=publicDescriptionUrl(card);
 const cells=["Abilità primaria","Tiri salvezza","Competenze"]
   .map(label=>data.highlights.find(item=>item.label===label)||{label,value:"",fullValue:""});
 return <div ref={ref} data-testid="card-front" data-front-category="class"
   data-front-layout="class-user-original-20261103"
   data-class-master-src="/card-art/class-user-original-20261103.jpg"
   className={"tf-class-user-master"+(exportMode?" tf-export-card":"")}
   style={frontBackground("class")}>
   <div className="tf-class-user-emblem tf-v3-medallion" data-testid="front-emblem"
    data-emblem-sprite={emblem?.sprite||"none"} title={emblem?.label||""}>
    {emblem&&<div className="tf-class-user-emblem-art tf-v3-sprite"
     aria-label={emblem.label} style={{
       backgroundImage:"url("+emblem.src+")",
       backgroundPosition:emblem.backgroundPosition,
       backgroundSize:emblem.backgroundSize
     }}/>}
   </div>
   <div className="tf-class-user-titles tf-v3-titles">
     {name&&<h3 title={name}>{name}</h3>}{name&&<p>Classe</p>}
   </div>
   <section className="tf-class-user-picture tf-v3-picture" aria-label="Illustrazione personalizzabile">
     {artSrc&&!artError
       ? <img src={artSrc} alt={name||"Illustrazione"} data-artwork-src={artSrc}
           crossOrigin="anonymous" onError={()=>setArtError(true)} draggable={false}/>
       : <span data-testid="front-artwork-empty" aria-hidden="true"/>}
     {artError&&editorMode&&!exportMode&&<span role="alert">Artwork non disponibile</span>}
   </section>
   <div className="tf-class-user-stats tf-v3-stats" data-testid="front-highlights">
    {cells.map(item=>{
      const icon=item.value?getFrontStatIcon(item.label):null;
      return <div className="tf-class-user-stat tf-v3-stat" data-stat-label={item.label}
       title={item.fullValue||item.value} key={item.label}>
       <div className="tf-v6-stat-text">
        {name&&<span>{item.label}</span>}
        <div className="tf-v6-stat-value-row">
         {icon&&<img className="tf-v6-stat-icon" src={icon} alt="" aria-hidden="true"/>}
         <strong>{item.value}</strong>
        </div>
       </div>
      </div>;
    })}
   </div>
   <section className="tf-class-user-parchment tf-v3-parchment" aria-label="Descrizione">
    <p className="tf-class-user-description tf-v3-desc" ref={textRef}>{description}</p>
   </section>
   {data.dice&&data.classDieAsset&&<div className="tf-class-user-die tf-v3-dice tf-class-hit-die"
     style={{backgroundImage:"url("+data.classDieAsset+")"}} data-die={data.dice}
     aria-label={"Dado vita "+data.dice}><span className="sr-only">{data.dice}</span></div>}
   {link&&<a href={link} className="tf-class-user-qr tf-v3-qr" data-card-qr
     title="Apri la descrizione completa" aria-label={"Descrizione completa di "+data.name}
     target="_blank" rel="noopener noreferrer">
      <QRCodeCanvas value={link} size={46} level="M" marginSize={1}
       bgColor="#ffffff" fgColor="#10131c"/>
   </a>}
 </div>;
});
ClassCardFront.displayName="ClassCardFront";
