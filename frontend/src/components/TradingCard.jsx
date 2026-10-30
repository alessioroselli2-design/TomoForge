import React from "react";
import { QRCodeCanvas } from "qrcode.react";
import { publicDescriptionUrl } from "@/lib/cardDescription";
import { FRONT_MASTER_URL, FRONT_DETAIL_REPAIR_URL } from "@/lib/frontMaster";
import { artworkUrl } from "@/lib/api";
import artworkPlaceholder from "@/assets/artwork-placeholder.svg";
import { getApprovedBack } from "@/lib/cardBacks";
import { buildFrontBlueprint } from "@/lib/cardFrontBlueprint";
import { getFrontStatIcon } from "@/lib/frontStatIcons";

export const CardFront = React.forwardRef(({ card, exportMode, editorMode, imgUrl }, ref) => {
 const data=buildFrontBlueprint(card);
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
 return <div ref={ref} data-testid="card-front" data-front-version="7"
   data-front-category={data.type} data-front-layout="reference-master-v7"
   className={`tf-front-v3 tf-front-v6 tf-front-master-v7 ${exportMode?"tf-export-card":""} ${data.hasAbilities?"tf-v3-six":""} ${data.name.length>=17?"tf-v6-long-title":""}`}
   style={{"--tf-v3-accent":data.accent,backgroundImage:`url(${FRONT_MASTER_URL})`}}>
   <span className="tf-v3-corner tf-v3-tl" aria-hidden="true">✦</span>
   <span className="tf-v3-corner tf-v3-tr" aria-hidden="true">✦</span>
   <span className="tf-v3-corner tf-v3-bl" aria-hidden="true">✦</span>
   <span className="tf-v3-corner tf-v3-br" aria-hidden="true">✦</span>
   <div className="tf-v3-layout">
     <header className="tf-v3-banner">
       <div className="tf-v3-medallion" data-testid="front-emblem"
         data-emblem-sprite={symbol?.sprite||"none"} title={symbol?.label||data.subtitle}>
         {symbol ? <>
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
       <img src={img} data-artwork-src={img} data-is-placeholder={!hasArtwork||artworkError} alt={data.name} crossOrigin="anonymous" onError={handleError} draggable={false}/>
       {editorMode&&!hasArtwork&&<span className="tf-v3-art-hint">CARICA O GENERA L'ILLUSTRAZIONE</span>}
       {artworkError&&!exportMode&&<span role="alert" className="tf-v3-art-warning"><span aria-hidden="true">⚠</span> Artwork non disponibile</span>}
     </section>
     <div className="tf-v3-stats" data-testid="front-highlights">
       {data.highlights.length?data.highlights.map((item,i)=>{
         const statIcon = getFrontStatIcon(item.label);
         return <div className={`tf-v3-stat ${statIcon?"tf-v6-stat-with-icon":""}`}
           key={i} title={item.fullValue||item.value} data-stat-label={item.label}>
           {statIcon&&<img className="tf-v6-stat-icon" src={statIcon} alt="" aria-hidden="true" draggable={false}/>}
           <div className="tf-v6-stat-text"><span>{item.label}</span><strong>{item.value}</strong></div>
         </div>;
       }):<div className="tf-v3-stat tf-v3-empty">I DATI COMPARRANNO QUI</div>}
     </div>
     {data.hasAbilities&&<div className="tf-v3-abilities" data-testid="front-abilities">
       {data.abilities.map(item=><div className="tf-v3-ability" key={item.label}>
         <span>{item.label}</span><strong>{item.value}</strong>
       </div>)}
     </div>}
     <section className="tf-v3-parchment" aria-label="Dati della carta">
       {data.details.length>0&&<div className={`tf-v3-details ${data.type==="monster"?"tf-v5-monster-details":""}`}>
         {data.details.slice(0,2).map((item,i)=><div className="tf-v5-detail-cell" key={item.key||i}><b>{item.label}</b><span>{item.value}</span></div>)}
       </div>}
       <span className="tf-v7-description-label">Descrizione</span>
       <p className="tf-v3-desc">{data.description||"I dettagli appariranno dopo la selezione di un record."}</p>
       {data.dice&&<div className="tf-v3-dice" aria-label={`Formula dado ${data.dice}`}>{data.dice}</div>}
       {detailsLink&&<a className="tf-v3-qr" data-card-qr href={detailsLink}
           target="_blank" rel="noopener noreferrer" title="Apri la descrizione completa"
           aria-label={`Apri la descrizione completa di ${data.name}`}>
         <QRCodeCanvas value={detailsLink} size={46} level="M" marginSize={1}
            bgColor="#ffffff" fgColor="#10131c" />
       </a>}
     </section>
   </div>
   {/* Only the erased paper texture is repaired; all goldwork remains the approved master. */}
   <img className="tf-v8-detail-repair" data-front-detail-repair src={FRONT_DETAIL_REPAIR_URL}
     alt="" aria-hidden="true" draggable={false}/>

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
