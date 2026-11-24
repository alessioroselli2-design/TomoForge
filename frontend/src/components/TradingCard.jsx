import React from "react";
import { QRCodeCanvas } from "qrcode.react";
import { publicDescriptionUrl } from "@/lib/cardDescription";
import { categoryFrontLayout, frontBackground } from "@/lib/frontCategoryLayouts";
import { artworkUrl } from "@/lib/api";
import artworkPlaceholder from "@/assets/artwork-placeholder.svg";
import { getApprovedBack } from "@/lib/cardBacks";
import { CARD_EDGE_COLOR, CARD_ART_SCALE, backImageStyle } from "@/lib/cardPrintGeometry";
import { buildFrontBlueprint } from "@/lib/cardFrontBlueprint";
import { getFrontStatIcon } from "@/lib/frontStatIcons";
import { getClassPrimaryAbilityIcons } from "@/lib/classPrimaryAbilityIcons";
import { fitClassDescription } from "@/lib/classDescriptionFit";
import { SpellCardFront } from "@/components/SpellCardFront";
import { FeatureCardFront } from "@/components/FeatureCardFront";
import { RaceCardFront, RaceCardErrorBoundary } from "@/components/RaceCardFront";
import { CategoryCardFront } from "@/components/CategoryCardFront";
import { isCategoryMaster } from "@/lib/categoryCardView";

const LegacyCardFront = React.forwardRef(({ card, exportMode, editorMode, imgUrl }, ref) => {
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
 const [printedClassDescription,setPrintedClassDescription]=React.useState(data.description);
 React.useLayoutEffect(()=>{
   if(data.type!=="class")return undefined;
   const node=descriptionRef.current;
   if(!node)return undefined;
   let disposed=false;
   const update=()=>{
     if(disposed)return;
     const width=node.clientWidth,height=node.clientHeight;
     if(width<=0||height<=0){setPrintedClassDescription(data.description);return;}
     const style=window.getComputedStyle(node);
     const probe=document.createElement("div");
     Object.assign(probe.style,{
       position:"fixed",left:"-10000px",top:"-10000px",visibility:"hidden",
       boxSizing:"border-box",width:`${width}px`,height:"auto",maxHeight:"none",
       margin:"0",padding:"0",border:"0",overflow:"visible",
       fontFamily:style.fontFamily,fontSize:style.fontSize,fontWeight:style.fontWeight,
       lineHeight:style.lineHeight,letterSpacing:style.letterSpacing,
       overflowWrap:style.overflowWrap,whiteSpace:"normal",
     });
     document.body.appendChild(probe);
     try{
       const fitted=fitClassDescription(data.fullDescription,text=>{
         probe.textContent=text;
         return probe.getBoundingClientRect().height<=height+.5;
       });
       setPrintedClassDescription(fitted);
     }finally{probe.remove();}
   };
   update();
   const observer=typeof ResizeObserver!=="undefined"?new ResizeObserver(update):null;
   observer?.observe(node);
   if(document.fonts?.ready)document.fonts.ready.then(update).catch(()=>{});
   return ()=>{disposed=true;observer?.disconnect();};
 },[data.type,data.fullDescription,data.description]);
 // Every category shares the exact Monster v17 illustrated master.
 // Only data and inner content differ; never compose a second decorative plate.
 return <div ref={ref} data-testid="card-front" data-front-version="7"
   data-front-category={data.type} data-record-category={data.recordType || undefined} data-front-layout="unified-monster-master-v17" data-category-layout={layout.id}
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
            : symbol?.sprite==="school-original"
              ? <div className="tf-school-original-emblem" style={{backgroundImage:`url(${symbol.src})`}}
                  role="img" aria-label={symbol.label||""}/>
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
       {editorMode&&data.type!=="class"&&!hasArtwork&&<span className="tf-v3-art-hint">CARICA O GENERA L'ILLUSTRAZIONE</span>}
       {artworkError&&!exportMode&&<span role="alert" className="tf-v3-art-warning"><span aria-hidden="true">⚠</span> Artwork non disponibile</span>}
     </section>
     <div className="tf-v3-stats" data-testid="front-highlights">
       {data.highlights.length?data.highlights.map((item,i)=>{
         const isClass = data.type === "class";
         const isClassPrimary = isClass && item.label === "Abilità primaria";
         const primaryIcons = isClassPrimary
           ? getClassPrimaryAbilityIcons(item.fullValue || item.value) : [];
         // Do not duplicate shield and swords, already printed on the Class raster.
         const statIcon = isClass ? null : getFrontStatIcon(item.label);
         return <div className={`tf-v3-stat ${(statIcon||isClass)?"tf-v6-stat-with-icon":""}`}
           key={i} title={item.fullValue||item.value} data-stat-label={item.label}>
           <div className="tf-v6-stat-text">
             <span>{isClass ? ({ "Abilità primaria":"Abilità Primaria","Tiri salvezza":"Tiri Salvezza","Competenze":"Competenze" }[item.label] || item.label) : item.label}</span>
             {isClass
               ? <div className={`tf-v6-stat-value-row ${isClassPrimary?"tf-class-primary-row":"tf-class-static-row"} ${primaryIcons.length>1?"tf-class-primary-double":""}`}>
                   {primaryIcons.length>0&&<span className="tf-class-primary-icons" aria-hidden="true">
                     {primaryIcons.map(({name,src})=><img key={name} src={src} alt="" draggable={false}/>)}
                   </span>}
                   <strong>{item.value}</strong>
                 </div>
               : statIcon
                 ? <div className="tf-v6-stat-value-row">
                     <img className="tf-v6-stat-icon" src={statIcon} alt="" aria-hidden="true" draggable={false}/>
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
       <p ref={data.type==="class"?descriptionRef:undefined} className="tf-v3-desc">{(data.type==="class"?printedClassDescription:data.description)||"I dettagli appariranno dopo la selezione di un record."}</p>
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
LegacyCardFront.displayName="LegacyCardFront";
//
// All app surfaces (editor, detail, saved cards and print-sheet previews) now
// use exactly the approved Spell master. Other categories retain their renderer.
const ApprovedCardFront = React.forwardRef((props, ref) =>
  props.card?.type === "spell"
    ? <SpellCardFront {...props} ref={ref} />
    : props.card?.type === "feature"
      ? <FeatureCardFront {...props} ref={ref} />
      : props.card?.type === "race"
        ? <RaceCardErrorBoundary><RaceCardFront {...props} ref={ref} /></RaceCardErrorBoundary>
        : isCategoryMaster(props.card?.type)
          ? <CategoryCardFront {...props} ref={ref} />
          : <LegacyCardFront {...props} ref={ref} />
);
ApprovedCardFront.displayName="ApprovedCardFront";

// Scaling the artwork layer (rather than its layout box) preserves all
// existing container measurements, text fitting and approved medallions.
function CardPrintSurface({children}){
 return <div data-card-print-surface="v1" className="relative h-full w-full overflow-hidden"
   style={{backgroundColor:CARD_EDGE_COLOR}}>
   <div className="absolute inset-0 overflow-hidden"
     style={{transform:`scale(${CARD_ART_SCALE})`,transformOrigin:"center"}}>
     {children}
   </div>
 </div>;
}
export const CardFront=React.forwardRef((props,ref)=>
 <CardPrintSurface><ApprovedCardFront {...props} ref={ref}/></CardPrintSurface>
);
CardFront.displayName="CardFront";

export const CardBack=React.forwardRef(({card,exportMode},ref)=>{
 const back=getApprovedBack(card);
 return <CardPrintSurface><div ref={ref} data-testid="card-back" data-back-asset={back.file}
   className={`relative h-full w-full overflow-hidden bg-[#101019] ${exportMode?"tf-export-card":""}`}>
    <img src={back.src} alt={`Retro ufficiale TomoForge: ${back.label}`}
    className="absolute block" style={backImageStyle(back.file)} draggable={false}/>
 </div></CardPrintSurface>;
});
CardBack.displayName="CardBack";
