import React from "react";
import { QRCodeCanvas } from "qrcode.react";
import { publicDescriptionUrl } from "@/lib/cardDescription";
import { categoryFrontLayout, frontBackground } from "@/lib/frontCategoryLayouts";
import { artworkUrl } from "@/lib/api";
import artworkPlaceholder from "@/assets/artwork-placeholder.svg";
import { getApprovedBack } from "@/lib/cardBacks";
import { buildFrontBlueprint } from "@/lib/cardFrontBlueprint";
import { getFrontStatIcon, getClassAbilityIcon } from "@/lib/frontStatIcons";
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
 const proficiencyRef=React.useRef(null);
 const [printedClassDescription,setPrintedClassDescription]=React.useState(data.description);
 const [descriptionSize,setDescriptionSize]=React.useState(8.5);
 const [proficiencySize,setProficiencySize]=React.useState(8.5);
 const [firstSentenceFallback,setFirstSentenceFallback]=React.useState(false);
 const primaryIcon=data.type==="class"?getClassAbilityIcon(data.highlights[0]?.value):"";
 const proficiencyValue=data.highlights[2]?.value||"";
 // Measure the actual rendered paragraph, never a detached surrogate.
 // Perform the same pass after font loading and on card size changes.
 React.useLayoutEffect(()=>{
   if(data.type!=="class")return undefined;
   const node=descriptionRef.current;
   if(!node)return undefined;
   let disposed=false;
   const source=String(data.fullDescription||"").replace(/\s+/g," ").trim();
   const fits=(candidate,size)=>{
     node.style.setProperty("--tf-class-description-size",`${size}px`);
     node.textContent=candidate;
     return node.scrollHeight<=node.clientHeight+1 && node.scrollWidth<=node.clientWidth+1;
   };
   const update=()=>{
     if(disposed||!node.isConnected)return;
     if(node.clientWidth<1||node.clientHeight<1)return;
     let fitted="",size=6.5;
     if(!source){
       fitted="";
     }else{
       for(let attempt=8.5;attempt>=6.5;attempt-=0.25){
         if(fits(source,attempt)){size=attempt;fitted=source;break;}
       }
       if(!fitted){
         size=6.5;
         fitted=fitClassDescription(source,candidate=>fits(candidate,size));
       }
     }
     node.style.setProperty("--tf-class-description-size",`${size}px`);
     node.textContent=fitted;
     const ends=[...source.matchAll(/[.!?](?=\s|$)/g)].map(m=>m.index+1);
     const fallback=!!(source&&fitted&&fitted!==source&&!ends.some(end=>source.slice(0,end).trim()===fitted));
     setFirstSentenceFallback(fallback);
     setDescriptionSize(size);
     setPrintedClassDescription(fitted);
   };
   update();
   const observer=typeof ResizeObserver==="function"?new ResizeObserver(update):null;
   observer?.observe(node);
   document.fonts?.ready?.then(update).catch(()=>{});
   const raf=typeof requestAnimationFrame==="function"?requestAnimationFrame(update):null;
   return ()=>{disposed=true;observer?.disconnect();
     if(raf!==null&&typeof cancelAnimationFrame==="function")cancelAnimationFrame(raf);};
 },[data.type,data.fullDescription]);
 React.useLayoutEffect(()=>{
   if(data.type!=="class")return undefined;
   const node=proficiencyRef.current;
   if(!node)return undefined;
   let disposed=false;
   const update=()=>{
     if(disposed||!node.isConnected||node.clientWidth<1)return;
     let size=6.5;
     for(let attempt=8.5;attempt>=6.5;attempt-=0.25){
       node.style.setProperty("--tf-class-proficiency-font",`${attempt}px`);
       if(node.scrollHeight<=node.clientHeight+1&&node.scrollWidth<=node.clientWidth+1){
         size=attempt;break;
       }
     }
     node.style.setProperty("--tf-class-proficiency-font",`${size}px`);
     setProficiencySize(size);
   };
   update();
   const observer=typeof ResizeObserver==="function"?new ResizeObserver(update):null;
   observer?.observe(node);
   document.fonts?.ready?.then(update).catch(()=>{});
   return ()=>{disposed=true;observer?.disconnect();};
 },[data.type,proficiencyValue]);
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
         {symbol?.sprite==="class-original"
           ? <img className="tf-class-original-emblem" src={symbol.src} alt={symbol.label||""} draggable={false}/>
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
     <div className="tf-v3-stats" data-testid="front-highlights">
       {data.highlights.length?data.highlights.map((item,i)=>{
         const statIcon = data.type==="class"?null:getFrontStatIcon(item.label);
         return <div className={`tf-v3-stat ${statIcon?"tf-v6-stat-with-icon":""}`}
           key={i} title={item.fullValue||item.value} data-stat-label={item.label}>
           {data.type==="class"
             ? <div className="tf-class-stat-value">
                 <strong ref={i===2?proficiencyRef:undefined}
                    style={i===2?{"--tf-class-proficiency-font":`${proficiencySize}px`}:undefined}>
                   {item.value}
                 </strong>
               </div>
             : <div className="tf-v6-stat-text">
               <span>{item.label}</span>
               {statIcon
                 ? <div className="tf-v6-stat-value-row">
                     <img className="tf-v6-stat-icon" src={statIcon} alt="" aria-hidden="true" draggable={false}/>
                     <strong>{item.value}</strong>
                   </div>
                 : <strong>{item.value}</strong>}
             </div>}
         </div>;
       }):<div className="tf-v3-stat tf-v3-empty">I DATI COMPARRANNO QUI</div>}
     </div>
     {data.type==="class"&&primaryIcon&&
       <span className="tf-class-primary-stamp" aria-hidden="true">
         <img src={primaryIcon} alt="" draggable={false}/>
       </span>}
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
       <p ref={data.type==="class"?descriptionRef:undefined} className="tf-v3-desc" data-class-first-sentence-fallback={data.type==="class"?String(firstSentenceFallback):undefined} style={data.type==="class"?{"--tf-class-description-size":`${descriptionSize}px`}:undefined}>{(data.type==="class"?printedClassDescription:data.description)||"I dettagli appariranno dopo la selezione di un record."}</p>
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
