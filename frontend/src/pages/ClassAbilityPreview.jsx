import React from "react";
import { CardFront } from "@/components/TradingCard";

// Fixtures exclusively for read-only preview; production continues to read
// each class' real abilita_primaria from verified app data.
const CLASSES = [
  ["Barbaro","Forza","d12"],
  ["Bardo","Carisma","d8"],
  ["Chierico","Saggezza","d8"],
  ["Druido","Saggezza","d8"],
  ["Guerriero","Forza o Destrezza","d10"],
  ["Ladro","Destrezza","d8"],
  ["Mago","Intelligenza","d6"],
  ["Monaco","Destrezza e Saggezza","d8"],
  ["Paladino","Forza e Carisma","d10"],
  ["Ranger","Destrezza e Saggezza","d10"],
  ["Stregone","Carisma","d6"],
  ["Warlock","Carisma","d8"],
  ["Artefice","Intelligenza","d8"],
];

export default function ClassAbilityPreview() {
  const [index,setIndex]=React.useState(0);
  const [name,primary,die]=CLASSES[index];
  const card={
    type:"class",name,
    description:`${name} è una classe di Dungeons & Dragons. Questa scheda dimostrativa consente di verificare la grafica delle caratteristiche primarie senza modificare alcun dato.`,
    attributes:{
      dado_vita:die,
      abilita_primaria:primary,
      tiri_salvezza:"Forza, Costituzione",
      competenze:"Armature, scudi e armi",
    },
  };
  return <main className="min-h-screen bg-obsidian text-gold px-3 py-8" data-testid="class-abilities-preview">
    <div className="mx-auto max-w-4xl">
      <h1 className="font-display text-2xl text-center">TomoForge · Anteprima Classi</h1>
      <p className="text-center text-sm mt-2 mb-4 text-foreground/70">
        Prova in sola lettura del renderer reale. Non modifica Supabase né le carte salvate.
      </p>
      <p className="text-center text-xs mb-5 text-foreground/70">
        Le caratteristiche in questa pagina sono esempi di collaudo. Il master definitivo non è ancora stato sostituito.
      </p>
      <div className="flex flex-wrap justify-center gap-2 mb-5">
        {CLASSES.map(([label],i)=><button key={label} type="button"
          onClick={()=>setIndex(i)} aria-pressed={index===i}
          className={`border rounded px-3 py-2 text-sm ${i===index?"bg-gold text-obsidian border-gold":"border-gold-deep text-gold"}`}>
          {label}
        </button>)}
      </div>
      <p className="text-center mb-4 text-sm">{name} · {primary} · {die}</p>
      <div className="mx-auto" style={{width:320,aspectRatio:"2.5 / 3.5"}}>
        <CardFront card={card} editorMode />
      </div>
    </div>
  </main>;
}
