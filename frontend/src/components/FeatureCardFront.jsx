import React from "react";
import { QRCodeCanvas } from "qrcode.react";
import { artworkUrl } from "@/lib/api";
import { publicDescriptionUrl } from "@/lib/cardDescription";
import { getFrontEmblem } from "@/lib/frontEmblems";
import { buildFeatureCardView } from "@/lib/featureCardView";
import "./FeatureCardFront.css";

const FIELDS = [
 {key:"activation", label:"Tipo di attivazione", icon:"/card-art/feature-icons/attivazione.svg"},
 {key:"uses", label:"Utilizzi disponibili", icon:"/card-art/feature-icons/utilizzi.svg"},
 {key:"recovery", label:"Recupero utilizzi", icon:"/card-art/feature-icons/recupero.svg"},
];
export const FeatureCardFront = React.forwardRef(
 ({card={},imgUrl,editorMode,exportMode},ref) => {
  const view=buildFeatureCardView(card);
  const emblem=getFrontEmblem({...card,type:"feature"});
  const [imageError,setImageError]=React.useState(false);
  const hasArtwork=Boolean(imgUrl||card.artwork_path);
  const imageSrc=imgUrl||(card.artwork_path?artworkUrl(card.artwork_path):"");
  React.useEffect(()=>setImageError(false),[imageSrc]);
  const detailsLink=publicDescriptionUrl(card);
  return <div ref={ref} data-testid="card-front" data-front-version="7"
   data-front-category="feature" data-front-layout="feature-5x7-v3"
   data-category-layout="feature-5x7-v3"
   className={"tf-feature-master"+(exportMode?" tf-export-card":"")}>
    <div className="tf-feature-medallion" data-testid="front-emblem"
      data-emblem-sprite={emblem?.sprite||"none"}>
      {emblem && <img className="tf-feature-original-emblem" src={emblem.src} alt="Simbolo Privilegi di classe" draggable={false}/>}
    </div>
    <header className="tf-feature-heading">
      <h3 title={view.name}>{view.name}</h3><p>{view.subtitle}</p>
    </header>
    {view.level&&<div className="tf-feature-level" aria-label={"Livello "+view.level}>
       <strong>{view.level}</strong><span>LIV.</span>
    </div>}
    <section className="tf-feature-artwork" aria-label="Illustrazione del privilegio">
      {hasArtwork&&!imageError&&<img src={imageSrc} alt={view.name}
       crossOrigin="anonymous" data-artwork-src={imageSrc} draggable={false}
       onError={()=>setImageError(true)}/>}
    </section>
    <section className="tf-feature-stats" data-testid="feature-stats" aria-label="Attivazione, utilizzi e recupero">
      {FIELDS.map(field=><div className="tf-feature-stat" data-feature-field={field.key} key={field.key}>
        <span className="tf-feature-stat-title">{field.label}</span>
        <div className="tf-feature-stat-body">
          <img src={field.icon} alt="" aria-hidden="true" draggable={false}/>
          {view[field.key]&&<strong title={view[field.key]}>{view[field.key]}</strong>}
        </div>
      </div>)}
    </section>
    <section className="tf-feature-parchment" aria-label="Descrizione del privilegio">
      <p className="tf-feature-description" title={view.description}>
        {view.excerpt||"Descrizione non presente nel record."}
      </p>
    </section>
    <section className="tf-feature-progression" data-testid="feature-progression"
      aria-label="Progressione del privilegio">
      {view.progression&&<>
        <strong>Progressione</strong>
        <p title={view.progression}>{view.progressionExcerpt}</p>
      </>}
    </section>
    {detailsLink&&<a className="tf-feature-qr" data-card-qr href={detailsLink}
      target="_blank" rel="noopener noreferrer" title="Apri descrizione completa"
      aria-label={"Apri la descrizione completa di "+view.name}>
      <QRCodeCanvas value={detailsLink} size={46} level="M" marginSize={1}
       bgColor="#ffffff" fgColor="#10131c"/>
    </a>}
  </div>;
});
FeatureCardFront.displayName="FeatureCardFront";
