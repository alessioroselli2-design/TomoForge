import React from "react";
import { QRCodeCanvas } from "qrcode.react";
import { artworkUrl } from "@/lib/api";
import { publicDescriptionUrl } from "@/lib/cardDescription";
import { getFrontEmblem } from "@/lib/frontEmblems";
import { buildFeatureCardView } from "@/lib/featureCardView";
import "./FeatureCardFront.css";

// Same approved 5:7 frame as Class, with an empty parchment illustration well.
// Class-only printed information is concealed by the feature's SINGLE inner panel.
export const FeatureCardFront = React.forwardRef(
 ({ card = {}, imgUrl, editorMode, exportMode }, ref) => {
  const view = buildFeatureCardView(card);
  const emblem = getFrontEmblem({ ...card, type: "feature" });
  const [artError, setArtError] = React.useState(false);
  const hasArt = Boolean(imgUrl || card.artwork_path);
  const src = imgUrl || (card.artwork_path ? artworkUrl(card.artwork_path) : "");
  React.useEffect(() => setArtError(false), [src]);
  const detailsLink = publicDescriptionUrl(card);
  const symbolStyle = emblem ? {
   backgroundImage: "url(" + JSON.stringify(emblem.src) + ")",
   backgroundPosition: emblem.backgroundPosition,
   backgroundSize: emblem.backgroundSize,
  } : undefined;
  return <div ref={ref} data-testid="card-front" data-front-version="7"
   data-front-category="feature" data-front-layout="feature-5x7-v1"
   data-category-layout="feature-5x7-v1"
   className={"tf-feature-master" + (exportMode ? " tf-export-card" : "")}>
   <div className="tf-feature-medallion" data-testid="front-emblem"
     data-emblem-sprite={emblem?.sprite || "none"} aria-label="Simbolo dei privilegi di classe">
     {emblem && <span className="tf-feature-emblem-icon" style={symbolStyle}/>}
   </div>
   <header className="tf-feature-heading">
    <h3 title={view.name}>{view.name}</h3>
    <p>{view.subtitle}</p>
   </header>
   {view.level && <div className="tf-feature-level" aria-label={"Livello " + view.level}>
     <strong>{view.level}</strong><span>LIV.</span>
   </div>}
   <section className="tf-feature-artwork" aria-label="Illustrazione del privilegio">
    {hasArt && !artError && <img src={src} data-artwork-src={src}
      crossOrigin="anonymous" alt={view.name} draggable={false}
      onError={() => setArtError(true)}/>}
    {editorMode && !hasArt && <span className="tf-feature-art-hint">Illustrazione facoltativa</span>}
   </section>
   <section className={"tf-feature-parchment" + (view.improvement ? " has-improvement" : "")}
      aria-label="Descrizione del privilegio">
    <p className="tf-feature-description" title={view.description}>
      {view.excerpt || "I dettagli del privilegio appariranno dopo la scelta del record."}
    </p>
    {view.improvement && <div className="tf-feature-improvement" data-testid="feature-improvements"
      title={view.improvement}>
      <strong>Miglioramenti</strong><p>{view.improvementExcerpt}</p>
    </div>}
   </section>
   {detailsLink && <a className="tf-feature-qr" data-card-qr
     href={detailsLink} target="_blank" rel="noopener noreferrer"
     aria-label={"Apri la descrizione completa di " + view.name}>
     <QRCodeCanvas value={detailsLink} size={46} level="M" marginSize={1}
       bgColor="#ffffff" fgColor="#10131c"/>
   </a>}
   <footer className="tf-feature-footer"><span>PRIVILEGI</span></footer>
  </div>;
 });
FeatureCardFront.displayName = "FeatureCardFront";
