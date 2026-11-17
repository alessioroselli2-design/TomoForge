import React from "react";
import { QRCodeCanvas } from "qrcode.react";
import { publicDescriptionUrl } from "@/lib/cardDescription";
import { categoryFrontLayout, frontBackground } from "@/lib/frontCategoryLayouts";
import { artworkUrl } from "@/lib/api";
import artworkPlaceholder from "@/assets/artwork-placeholder.svg";
import { getApprovedBack } from "@/lib/cardBacks";
import { buildFrontBlueprint } from "@/lib/cardFrontBlueprint";
import { getFrontStatIcon, getClassPrimaryIcon } from "@/lib/frontStatIcons";
import { fitClassDescription } from "@/lib/classDescriptionFit";

export const CardFront = React.forwardRef(({ card, exportMode, editorMode, imgUrl }, ref) => {
 const data=buildFrontBlueprint(card);
 const layout=categoryFrontLayout(data.type);
 const [artworkError,setArtworkError]=React.useState(false);
 React.useEffect(()=>setArtworkError(false),[imgUrl,card.artwork_path]);
 const hasArtwork=!!(imgUrl||card.artwork_path);
 const img=imgUrl||(card.artwork_path?artworkUrl(card.artwork_path):artworkPlaceholder);
 const handleError=React.useCallback(event=>{
   const src=event.currentTarget.dataset.artworkSrc;
   if(event.currentTarget.dataset.fallback!=="1"||event.currentTarget.dataset.fallbackSrc!==src){
     event.currentTarget.dataset.fallback="1";
     event.currentTarget.dataset.fallbackSrc=src;
     event.currentTarget.src=artworkPlaceholder;
     if(hasArtwork)setArtworkError(true);
   }
 },[hasArtwork]);
 const symbol=data.emblem;
 const detailsLink=publicDescriptionUrl(card);
 const descriptionRef=React.useRef(null);
 const highlightsRef=React.useRef(null);
 const [printedClassDescription,setPrintedClassDescription]=React.useState(data.description);
 const [classDescriptionSize,setClassDescriptionSize]=React.useState(8.5);
 const [firstSentenceFallback,setFirstSentenceFallback]=React.useState(false);
 React.useLayoutEffect(()=>{
   if(data.type!=="class")return undefined;
   const node=descriptionRef.current;
   if(!node)return undefined;
   let disposed=false;
   const source=String(data.fullDescription||data.description||"").replace(/\s+/g," ").trim();
   const fits=()=>node.scrollHeight<=node.clientHeight+1&&node.scrollWidth<=node.clientWidth+1;
   const measure=()=>{
     if(disposed||node.clientWidth===0||node.clientHeight===0)return;
     const original=node.textContent;
     let chosen="",size=6.5;
     // Prefer the largest readable font that fits the COMPLETE description.
     for(let attempt=8.5;attempt>=6.5;attempt-=.5){
       node.style.fontSize=`${attempt}px`;
       node.textContent=source;
       if(fits()){chosen=source;size=attempt;break;}
     }
     // At the minimum font, take only COMPLETE sentences that actually fit
     // in the visible paragraph, not a detached offscreen probe.
     if(!chosen){
       node.style.fontSize="6.5px";
       chosen=fitClassDescription(source,text=>{node.textContent=text;return fits();});
     }
     const firstEnd=source.search(/[.!?](?=\s|$)/);
     const firstSentence=firstEnd<0?source:source.slice(0,firstEnd+1);
     const fallback=!!source&&!!chosen&&!chosen.startsWith(firstSentence);
     node.textContent=original;
     node.style.fontSize=`${size}px`;
     setPrintedClassDescription(prev=>prev===chosen?prev:chosen);
     setClassDescriptionSize(prev=>prev===size?prev:size);
     setFirstSentenceFallback(prev=>prev===fallback?prev:fallback);
   };
   measure();
   const obs=typeof ResizeObserver!=="undefined"?new ResizeObserver(measure):null;
   obs?.observe(node);
   document.fonts?.ready?.then(()=>{if(!disposed)measure();}).catch(()=>{});
   return ()=>{disposed=true;obs?.disconnect();};
 },[data.type,data.fullDescription,data.description]);

 // The value is complete in the Class data model. Shrink each real stat
 // paragraph only until 6.5px; record unfit wells for test diagnostics.
 const classHighlightSignature=data.highlights.map(item=>item.value).join("|");
 React.useLayoutEffect(()=>{
   if(data.type!=="class"||!highlightsRef.current)return undefined;
   let dead=false;
   const measure=()=>{
     if(dead)return;
     highlightsRef.current?.querySelectorAll(".tf-v3-stat").forEach(well=>{
       const value=well.querySelector(".tf-v6-stat-value-row strong");
       const row=well.querySelector(".tf-v6-stat-value-row");
       if(!value||!row||!row.clientHeight)return;
       let size=8.5;
       for(;size>=6.5;size-=.5){
         value.style.setProperty("--tf-class-stat-size",`${size}px`);
         if(value.scrollHeight<=row.clientHeight+1&&value.scrollWidth<=value.clientWidth+1)break;
       }
       well.dataset.statOverflow=String(size<6.5);
     });
   };
   measure();
   const obs=typeof ResizeObserver!=="undefined"?new ResizeObserver(measure):null;
   obs?.observe(highlightsRef.current);
   document.fonts?.ready?.then(measure).catch(()=>{});
   return ()=>{dead=true;obs?.disconnect();};
 },[data.type,classHighlightSignature]);
 // Every category shares the exact Monster v17 illustrated master.
 // Only data and inner content differ; never compose a second decorative plate.
 return <div ref={ref} data-testid="card-front" data-front-version="7"
   data-front-category={data.type} data-front-layout="unified-monster-master-v17" data-category-layout={layout.id}
   className={`tf-front-v3 tf-front-v6 tf-front-master-v7 tf-front-master-v17 ${exportMode?"tf-export-card":""} ${data.hasAbilities?"tf-v3-six":""} ${data.name.length>=27?"tf-v6-extra-long-title":""} ${data.name.length>=17?"tf-v6-long-title":""}`}
   style={{"--tf-v3-accent":data.accent,...frontBackground(data.type)}}>
   <span className="tf-v3-corner tf-v3-tl" aria-hidden="true">✦</span>
   <span className="tf-v3-corner tf-v3-tr" aria-hidden="true">✦</span>
   <span className="tf-v3-corner tf-v3-bl" aria-hidden="true">✦</span>
   <span className="tf-v3-corner tf-v3-br" aria-hidden="true">✦</span>
   
   <div className="tf-v3-layout">
     <header className="tf-v3-banner">
       <div className="tf-v3-medallion" data-testid="front-emblem"
         data-emblem-sprite={symbol?.sprite||"none"} title={symbol?.label||data.subtitle}>
         {symbol?.sprite==="class-png"
           ? <img className="tf-class-emblem-img" src={symbol.src} alt={symbol.label||"Emblema classe"} draggable={false}/>
           : symbol ? <>
               <span className="tf-v3-fallback tf-v3-underlay" aria-hidden="true">✦</span>
               <div className="tf-v3-sprite" style={{backgroundImage:`url(${symbol.src})`,
                 backgroundPosition:symbol.backgroundPosition,backgroundSize:symbol.backgroundSize}} aria-label={symbol.label}/>
             </> : <span className="tf-v3-fallback">✦</span>}
       </div>
       <div className="tf-v3-titles">
         <h3 title={data.name}>{data.name}</h3>
         <p>{data.subtitle}</p>
       </div>
       {data.badge&&<div className="tf-v3-badge"><small>{data.badge.top}</small><strong>{data.badge.value}</strong></div>}
     </header>
     <section className="tf-v3-picture">
       {data.type==="class"&&(!hasArtwork||artworkError)
         ? <span data-testid="front-artwork-empty" aria-hidden="true"/>
         : <img src={img} data-artwork-src={img} data-is-placeholder={!hasArtwork||artworkError} alt={data.name} crossOrigin="anonymous" onError={handleError} draggable={false}/>}
       {editorMode&&!hasArtwork&&<span className="tf-v3-art-hint">CARICA O GENERA L'ILLUSTRAZIONE</span>}
       {artworkError&&!exportMode&&<span role="alert" className="tf-v3-art-warning"><span aria-hidden="true">⚠</span> Artwork non disponibile</span>}
     </section>
     <div ref={data.type==="class"?highlightsRef:undefined} className="tf-v3-stats" data-testid="front-highlights">
       {data.highlights.length?data.highlights.map((item,i)=>{
         const statIcon = data.type==="class"
           ? item.label==="Abilità primaria"?getClassPrimaryIcon(item.value):null
           : getFrontStatIcon(item.label);
         return <div className={`tf-v3-stat ${statIcon?"tf-v6-stat-with-icon":""}`}
           key={i} title={item.fullValue||item.value} data-stat-label={item.label}>
           <div className="tf-v6-stat-text">
             <span>{item.label}</span>
             {statIcon||data.type==="class"
               ? <div className="tf-v6-stat-value-row">
                   {statIcon&&<img className="tf-v6-stat-icon" src={statIcon} alt="" aria-hidden="true" draggable={false}/>}
                   <strong>{item.value}</strong>
                 </div>
               : <strong>{item.value}</strong>}
           </div>
         </div>;
       }):<div className="tf-v3-stat tf-v3-empty">I DATI COMPARRANNO QUI</div>}
     </div>
     {data.hasAbilities&&<div className="tf-v3-abilities" data-testid="front-abilities">
       {data.abilities.map(item=><div className="tf-v3-ability" key={item.label}>
         <span>{item.label}</span><strong>{item.value}</strong>
       </div>)}
     </div>}
     <section className="tf-v3-parchment" aria-label="Dati della carta">
       {layout.showDetails&&data.details.length>0&&<div className={`tf-v3-details ${data.type==="monster"?"tf-v5-monster-details":""}`}>
         {data.details.slice(0,2).map((item,i)=><div className="tf-v5-detail-cell" key={item.key||i}><b>{item.label}</b><span>{item.value}</span></div>)}
       </div>}
       {data.showDescriptionLabel&&<span className="tf-v7-description-label">Descrizione</span>}
       <p ref={data.type==="class"?descriptionRef:undefined} className="tf-v3-desc" data-first-sentence-fallback={data.type==="class"?String(firstSentenceFallback):undefined} style={data.type==="class"?{fontSize:`${classDescriptionSize}px`}:undefined}>{(data.type==="class"?printedClassDescription:data.description)||"I dettagli appariranno dopo la selezione di un record."}</p>
       {data.dice&&(data.type==="spell"&&data.spellDieAsset
         ? <div className="tf-v3-spell-dice" data-die={data.spellDie} aria-label={`Danni ${data.dice}`}>
             <img src={data.spellDieAsset} alt="" aria-hidden="true" draggable={false}/>
             <strong className="tf-v3-spell-formula" style={{fontSize:
               data.dice.length<=3?"21px":data.dice.length<=4?"18px":data.dice.length<=5?"15px":"12px"
             }}>{data.dice}</strong>
           </div>
         : <div className={`tf-v3-dice ${data.type==="class"?"tf-class-hit-die":""}`} data-die={data.dice} style={data.classDieAsset?{backgroundImage:`url("${data.classDieAsset}")`}:undefined} aria-label={data.type==="class"?`Dado vita ${data.dice}`:`Formula dado ${data.dice}`}>{data.classDieAsset?<span className="sr-only">{data.dice}</span>:data.dice}</div>)}
       {detailsLink&&<a className="tf-v3-qr" data-card-qr href={detailsLink}
           target="_blank" rel="noopener noreferrer" title="Apri la descrizione completa"
           aria-label={`Apri la descrizione completa di ${data.name}`}>
         <QRCodeCanvas value={detailsLink} size={46} level="M" marginSize={1}
            bgColor="#ffffff" fgColor="#10131c" />
       </a>}
     </section>
   </div>

 </div>;
});
CardFront.displayName="CardFront";

export const CardBack=React.forwardRef(({card,exportMode},ref)=>{
 const back=getApprovedBack(card);
 return <div ref={ref} data-testid="card-back" data-back-asset={back.file}
   className={`relative h-full w-full overflow-hidden bg-[#101019] ${exportMode?"tf-export-card":""}`}>
    <img src={back.src} alt={`Retro ufficiale TomoForge: ${back.label}`}
    className="absolute inset-0 block h-full w-full" style={{objectFit:"contain"}} draggable={false}/>
 </div>;
});
CardBack.displayName="CardBack";
