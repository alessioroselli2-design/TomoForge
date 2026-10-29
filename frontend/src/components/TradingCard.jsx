import React from "react";
import { artworkUrl } from "@/lib/api";
import artworkPlaceholder from "@/assets/artwork-placeholder.svg";
import { getApprovedBack } from "@/lib/cardBacks";
import { buildFrontBlueprint } from "@/lib/cardFrontBlueprint";

export const CardFront = React.forwardRef(({ card, exportMode, editorMode, imgUrl }, ref) => {
  const blueprint = buildFrontBlueprint(card);
  const [artworkError, setArtworkError] = React.useState(false);
  React.useEffect(() => setArtworkError(false), [imgUrl, card.artwork_path]);
  const hasArtwork = !!(imgUrl || card.artwork_path);
  const img = imgUrl || (card.artwork_path ? artworkUrl(card.artwork_path) : artworkPlaceholder);
  const handleError = React.useCallback((event) => {
    if (event.currentTarget.dataset.fallback !== "1") {
      event.currentTarget.dataset.fallback = "1";
      event.currentTarget.src = artworkPlaceholder;
      if (hasArtwork) setArtworkError(true);
    }
  }, [hasArtwork]);

  return (
    <div
      ref={ref}
      data-testid="card-front"
      data-front-version="2"
      data-front-category={blueprint.type}
      className={`tf-front-v2 ${exportMode ? "tf-export-card" : ""}`}
      style={{ "--tf-front-accent": blueprint.accent, "--tf-front-shadow": blueprint.shadow }}
    >
      <div className={`tf-v2-layout ${blueprint.hasAbilities ? "tf-v2-with-abilities" : ""}`}>
        <header className="tf-v2-header">
          <span className="tf-v2-overline">{blueprint.heading} <span aria-hidden="true">✦</span> TOMOFORGE</span>
          <h3 className="tf-v2-title" title={blueprint.name}>{blueprint.name}</h3>
          <p className="tf-v2-subtitle">{blueprint.subtitle}</p>
          <div className="tf-v2-crest" title={blueprint.subtitle} aria-label={`Sigillo ${blueprint.subtitle}`}>
            {blueprint.crest}
          </div>
        </header>

        <div className="tf-v2-artwork">
          <img src={img} alt={blueprint.name} data-artwork-src={img} crossOrigin="anonymous"
            onError={handleError} draggable={false} />
          {editorMode && !hasArtwork && <span className="tf-v2-art-hint">CARICA O GENERA L'ILLUSTRAZIONE</span>}
          {artworkError && !exportMode && <span role="alert" className="tf-v2-art-warning">Immagine non disponibile</span>}
          {blueprint.dice && <span className="tf-v2-dice" aria-label={`Formula dado ${blueprint.dice}`}>{blueprint.dice}</span>}
        </div>

        <div className="tf-v2-stats" data-testid="front-highlights">
          {blueprint.highlights.length ? blueprint.highlights.map((entry) => (
            <div key={entry.label} className="tf-v2-stat">
              <span>{entry.label}</span><strong title={entry.value}>{entry.value}</strong>
            </div>
          )) : <div className="tf-v2-stat tf-v2-stat-empty"><span>IN ATTESA DEI DATI DELLA CARTA</span></div>}
        </div>

        {blueprint.hasAbilities && <div className="tf-v2-abilities" data-testid="front-abilities">
          {blueprint.abilities.map((entry) => (
            <div key={entry.label} className="tf-v2-ability"><span>{entry.label}</span><strong>{entry.value}</strong></div>
          ))}
        </div>}

        <section className="tf-v2-details" aria-label="Dati della carta">
          {blueprint.details.length > 0 && <p className="tf-v2-detail-line">
            {blueprint.details.map((entry) => <span key={entry.label}><b>{entry.label}</b> {entry.value}</span>)}
          </p>}
          <p className="tf-v2-description">{blueprint.description || "Le informazioni della carta appariranno qui dopo la selezione di un record."}</p>
        </section>
        <footer className="tf-v2-footer"><span>✦ TOMOFORGE</span><span>{blueprint.heading}</span></footer>
      </div>
    </div>
  );
});
CardFront.displayName = "CardFront";

export const CardBack = React.forwardRef(({ card, exportMode }, ref) => {
  // Official approved art is selected by type, independently of the new front.
  const back = getApprovedBack(card);
  return (
    <div ref={ref} data-testid="card-back" data-back-asset={back.file}
      className={`relative h-full w-full overflow-hidden bg-[#101019] ${exportMode ? "tf-export-card" : ""}`}>
      <img src={back.src} alt={`Retro ufficiale TomoForge: ${back.label}`}
        className="absolute inset-0 block h-full w-full" style={{ objectFit: "contain" }} draggable={false} />
    </div>
  );
});
CardBack.displayName = "CardBack";
