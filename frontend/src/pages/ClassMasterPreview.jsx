import React from "react";
import { CardFront } from "@/components/TradingCard";

const CLASS_MASTER = "/card-art/master-classe-pulito-v49.webp";
const HIT_DIE=Object.freeze({Barbaro:"d12",Bardo:"d8",Chierico:"d8",Druido:"d8",Guerriero:"d10",Monaco:"d8",Paladino:"d10",Ranger:"d10",Ladro:"d8",Stregone:"d6",Warlock:"d8",Mago:"d6",Artefice:"d8"});
const CLASS_NAMES = ["Barbaro","Bardo","Chierico","Druido","Guerriero","Monaco","Paladino","Ranger","Ladro","Stregone","Warlock","Mago","Artefice"];

// Standalone read-only acceptance preview: no API, login, drafts or records.
// A single raster is the complete decorative master. CardFront overlays only
// user-provided fields and uploaded artwork; no replacement frame is generated.
const EXAMPLES = {
  empty: {
    type: "class", name: "", description: "", attributes: {},
  },
  warrior: {
    type: "class", name: "Guerriero",
    description: "Maestri del combattimento, i guerrieri uniscono addestramento, disciplina e resistenza per eccellere in battaglia.",
    attributes: {
      abilita_primaria: "Forza o Destrezza",
      tiri_salvezza: "Forza, Costituzione",
      competenze: "Tutte le armature, scudi, armi semplici e da guerra",
      dado_vita: "d10",
    },
  },
  druid: {
    type: "class", name: "Druido",
    description: "I druidi custodiscono la natura e attingono alla sua magia, mantenendo l'equilibrio tra le creature e le forze del mondo.",
    attributes: {
      abilita_primaria: "Saggezza",
      tiri_salvezza: "Intelligenza, Saggezza",
      competenze: "Armature leggere e medie, scudi, kit da erborista",
      dado_vita: "d8",
    },
  },
};

export default function ClassMasterPreview() {
  const [variant, setVariant] = React.useState("warrior");
  // Other classes exercise the real emblem mapper without inventing statistics.
  const card = EXAMPLES[variant] || {type:"class",name:variant.replace(/^class:/,""),description:"",attributes:{dado_vita:HIT_DIE[variant.replace(/^class:/,"")]}};
  return (
    <main className="min-h-screen bg-obsidian text-foreground px-3 py-7"
      data-testid="class-master-reference-20261103">
      <div className="max-w-5xl mx-auto text-center">
        <p className="font-label text-xs tracking-[.16em] text-gold">
          TOMOFORGE · COLLAUDO CLASSE · 3 NOVEMBRE 2026
        </p>
        <h1 className="text-gold font-display text-2xl sm:text-3xl mt-3">
          Cornice originale, senza sovrapposizioni
        </h1>
        <p className="font-body text-sm mt-3 text-foreground/80 max-w-2xl mx-auto">
          Questa pagina mostra la versione proposta, non il sito pubblico.
          La carta a sinistra e la fotografia originale; a destra e la stessa
          base con i soli campi dinamici. Nessuna decorazione viene ridisegnata.
        </p>
        <nav className="flex flex-wrap justify-center gap-2 mt-5 mb-6" aria-label="Prova carta Classe">
          {[
            ["empty", "Modello vuoto"],
            ["warrior", "Guerriero"],
            ["druid", "Druido"],
          ].map(([key, label]) => (
            <button key={key} type="button" onClick={() => setVariant(key)}
              aria-pressed={variant === key}
              className={`border px-4 py-2 text-sm ${variant === key ?
                "bg-gold text-obsidian border-gold" : "text-gold border-gold-deep"}`}>
              {label}
            </button>
          ))}
        </nav>
        <div className="flex flex-col items-center gap-1 mb-5">
          <label htmlFor="class-medal-check" className="text-gold text-sm font-label">
            Verifica il simbolo di tutte le 13 classi
          </label>
          <select id="class-medal-check" value={variant} onChange={event=>setVariant(event.target.value)}
            className="w-[min(340px,92vw)] bg-obsidian border border-gold-deep text-gold px-3 py-2 text-base">
            <option value="empty">Modello vuoto</option>
            <option value="warrior">Guerriero (dati di prova)</option>
            <option value="druid">Druido (dati di prova)</option>
            {CLASS_NAMES.filter(name=>!["Guerriero","Druido"].includes(name)).map(name=>
              <option key={name} value={"class:"+name}>{name} (solo simbolo e titolo)</option>)}
          </select>
        </div>
        <div className="flex flex-wrap justify-center items-start gap-6">
          <figure className="w-[min(340px,92vw)]">
            <img src={CLASS_MASTER} alt="Cornice originale approvata, vuota"
              className="block w-full h-auto" style={{ aspectRatio: "864 / 1210" }} />
            <figcaption className="text-gold text-xs mt-3 font-label">
              Master Classe pulito · senza dado inciso
            </figcaption>
          </figure>
          <figure className="w-[min(340px,92vw)]">
            <div className="w-full" style={{ aspectRatio: "340 / 476" }}>
              <CardFront card={card} />
            </div>
            <figcaption className="text-gold text-xs mt-3 font-label">
              Applicazione dinamica · {variant === "empty" ? "vuota" :
                variant === "warrior" ? "Guerriero" : variant === "druid" ? "Druido" : card.name}
            </figcaption>
          </figure>
        </div>
        <p className="font-body text-xs text-foreground/60 mt-5 max-w-xl mx-auto">
          Dimostrazione isolata: l'immagine rimane vuota finche non viene
          caricata un'illustrazione. I dati di prova non vengono salvati.
          Nessun cambiamento alla produzione o alle altre categorie.
        </p>
      </div>
    </main>
  );
}
