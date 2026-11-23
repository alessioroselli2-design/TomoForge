import React from "react";
import { CardFront } from "@/components/TradingCard";

// Only synthetic layout fixtures: never claim these are verified library records.
// Actual cards in the app always use the selected database record.
const FIXTURES=[
 {name:"Umano",size:"Media",speed:"9 m",dark:"",languages:"Comune"},
 {name:"Elfo",size:"Media",speed:"9 m",dark:"18 m",languages:"Comune, Elfico"},
 {name:"Nano",size:"Media",speed:"7,5 m",dark:"18 m",languages:"Comune, Nanico"},
 {name:"Dragonide",size:"Media",speed:"9 m",dark:"",languages:"Comune, Draconico"},
 {name:"Genasi",size:"Media",speed:"9 m",dark:"",languages:"Comune, Primordiale"},
 {name:"Goblin",size:"Piccola",speed:"9 m",dark:"18 m",languages:"Comune, Goblin"},
 {name:"Tabaxi",size:"Media",speed:"9 m",dark:"18 m",languages:"Comune, una lingua aggiuntiva"},
 {name:"Shifter",size:"Media",speed:"9 m",dark:"18 m",languages:"Comune"},
 {name:"Hadozee",size:"Media",speed:"9 m",dark:"",languages:"Comune, un'altra lingua"},
];
const SAMPLE_TRAITS=[
 {nome:"Tratto di verifica",descrizione:"Questo testo serve esclusivamente a controllare la disposizione grafica, il grassetto e la larghezza delle righe."},
 {nome:"Secondo tratto",descrizione:"Il contenuto dimostrativo deve terminare con una frase completa, senza sovrapporsi ai titoli stampati sul master."},
 {nome:"Terzo tratto",descrizione:"Un ulteriore paragrafo permette di controllare l'adattamento automatico della dimensione del carattere."},
 {nome:"Tratto aggiuntivo",descrizione:"Un testo più lungo che occupa alcune righe per verificare la capienza delle descrizioni e la rimozione dei soli tratti completi quando necessario."},
 {nome:"Ultimo tratto",descrizione:"Il suo posizionamento non deve interferire con le sottorazze o con il bordo decorativo."},
];
export default function RaceCardPreview(){
 const [index,setIndex]=React.useState(0);
 const [long,setLong]=React.useState(false);
 const [empty,setEmpty]=React.useState(false);
 const race=FIXTURES[index];
 const card=React.useMemo(()=>({type:"race",name:race.name,
  attributes:empty?{}:{
    taglia:race.size,velocita:race.speed,scurovisione:race.dark,
    linguaggi:race.languages,
    tratti:long?SAMPLE_TRAITS:SAMPLE_TRAITS.slice(0,2),
    sottorazze:long?"Prima variante · Seconda variante":"Variante dimostrativa",
  },
 }),[race,empty,long]);
 return <main className="min-h-screen bg-obsidian text-gold px-3 py-6 sm:py-10" data-testid="race-card-preview">
  <div className="mx-auto max-w-2xl text-center">
   <h1 className="text-2xl font-display">TomoForge · Prova carta Razza</h1>
   <p className="mt-2 mb-4 text-xs text-foreground/70">
    Anteprima del renderer reale 5×7 · nessun login, salvataggio, merge o modifica ai record.
    Le statistiche e i tratti mostrati sono <strong>esempi grafici</strong>, non dati dell'archivio.
   </p>
   <nav className="flex gap-2 justify-center flex-wrap mb-4" aria-label="Razze da verificare">
    {FIXTURES.map((item,i)=><button type="button" key={item.name}
      onClick={()=>setIndex(i)} aria-pressed={i===index}
      className={"border border-gold-deep rounded px-2 py-1 text-xs "+(index===i?"bg-gold text-obsidian":"text-gold")}>
      {item.name}</button>)}
   </nav>
   <div className="flex gap-4 justify-center mb-4 text-xs flex-wrap">
    <label><input type="checkbox" checked={long} onChange={e=>setLong(e.target.checked)}/> Test tratti lunghi</label>
    <label><input type="checkbox" checked={empty} onChange={e=>setEmpty(e.target.checked)}/> Test valori mancanti</label>
   </div>
   <div className="mx-auto" style={{width:"min(100%,360px)",aspectRatio:"5 / 7"}}>
    <CardFront card={card} editorMode/>
   </div>
   <p className="mt-4 text-xs text-foreground/60">PR #698 · prova solo della categoria Razza. La produzione rimane invariata.</p>
  </div>
 </main>;
}
