import React from "react";
import { artworkUrl } from "@/lib/api";
import artworkPlaceholder from "@/assets/artwork-placeholder.svg";
import { getApprovedBack } from "@/lib/cardBacks";
import { buildFrontBlueprint } from "@/lib/cardFrontBlueprint";

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
 return <div ref={ref} data-testid="card-front" data-front-version="3"
   data-front-category={data.type}
   className={`tf-front-v3 ${exportMode?"tf-export-card":""} ${data.hasAbilities?"tf-v3-six":""}`}
   style={{"--tf-v3-accent":data.accent}}>
   <span className="tf-v3-corner tf-v3-tl" aria-hidden="true">✦</span>
   <span className="tf-v3-corner tf-v3-tr" aria-hidden="true">✦</span>
   <span className="tf-v3-corner tf-v3-bl" aria-hidden="true">✦</span>
   <span className="tf-v3-corner tf-v3-br" aria-hidden="true">✦</span>
   <div className="tf-v3-layout">
     <header className="tf-v3-banner">
       <div className="tf-v3-medallion" data-testid="front-emblem" title={symbol?.label||data.subtitle}>
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
       <img src={img} data-artwork-src={img} alt={data.name} crossOrigin="anonymous" onError={handleError} draggable={false}/>
       {editorMode&&!hasArtwork&&<span className="tf-v3-art-hint">CARICA O GENERA L'ILLUSTRAZIONE</span>}
       {artworkError&&!exportMode&&<span role="alert" className="tf-v3-art-warning"><span aria-hidden="true">⚠</span> Artwork non disponibile</span>}
     </section>
     <div className="tf-v3-stats" data-testid="front-highlights">
       {data.highlights.length?data.highlights.map((item,i)=><div className="tf-v3-stat" key={i} title={item.fullValue||item.value}>
         <span>{item.label}</span><strong>{item.value}</strong>
       </div>):<div className="tf-v3-stat tf-v3-empty">I DATI COMPARRANNO QUI</div>}
     </div>
     {data.hasAbilities&&<div className="tf-v3-abilities" data-testid="front-abilities">
       {data.abilities.map(item=><div className="tf-v3-ability" key={item.label}>
         <span>{item.label}</span><strong>{item.value}</strong>
       </div>)}
     </div>}
     <section className="tf-v3-parchment" aria-label="Dati della carta">
       {data.details.length>0&&<p className="tf-v3-details">
         {data.details.map((item,i)=><span key={i}><b>{item.label}</b> {item.value}</span>)}
       </p>}
       <p className="tf-v3-desc">{data.description||"I dettagli appariranno dopo la selezione di un record."}</p>
       {data.dice&&<div className="tf-v3-dice" aria-label={`Formula dado ${data.dice}`}>{data.dice}</div>}
     </section>
     <footer className="tf-v3-category"><span>✦</span>{data.heading}<span>✦</span></footer>
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
