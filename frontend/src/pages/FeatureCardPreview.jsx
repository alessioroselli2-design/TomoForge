import React from "react";
import { CardFront } from "@/components/TradingCard";

// Read-only, public visual QA of the actual TomoForge renderer.
// These are declared fixture values, NOT a database entry and not 5e rules.
const FORMA_SELVATICA={
  type:"feature",name:"Forma Selvatica",
  description:"Come azione, puoi trasformarti in una bestia che conosci e che abbia un grado di sfida pari o inferiore a 1/4. Mantieni i tuoi punti ferita e puoi tornare alla tua forma normale come azione bonus.",
  attributes:{
    classe:"Druido",livello:"2",
    miglioramenti:"Il limite del grado di sfida aumenta ai livelli successivi.",
  },
};

export default function FeatureCardPreview(){
  return <main className="min-h-screen bg-obsidian text-gold px-3 py-6 sm:py-10"
    data-testid="feature-card-preview">
    <div className="mx-auto max-w-xl text-center">
      <h1 className="text-2xl font-display">TomoForge · Anteprima Privilegi</h1>
      <p className="text-sm text-foreground/75 mt-2 mb-5">
        Carta reale del ramo di prova, senza merge e senza accesso all'account.
      </p>
      <div className="mx-auto" style={{width:"min(100%,360px)",aspectRatio:"5 / 7"}}>
        <CardFront card={FORMA_SELVATICA} editorMode />
      </div>
      <div className="mt-5 mx-auto max-w-md text-sm text-foreground/80">
        <p>Forma Selvatica · esempio grafico con la finestra illustrazione vuota.</p>
        <p className="mt-2 text-xs text-foreground/60">
          Il testo è dimostrativo per controllare la grafica, non deriva da un record reale.
          Dopo l'approvazione, l'immagine e i valori saranno scelti in TomoForge.
        </p>
      </div>
    </div>
  </main>;
}
