import React from "react";
import {CardFront} from "@/components/TradingCard";
// Declared graphic fixtures. These are not saved to, or claimed to be from, the
// user's library; switch examples to test actual CSS on long/empty values.
const PREVIEWS=[
 {title:"Forma Selvatica",card:{type:"feature",name:"Forma Selvatica",
  description:"Come azione, un druido può assumere la forma di una bestia che ha già visto. Può utilizzare questo privilegio due volte e recupera gli utilizzi spesi al termine di un riposo breve o lungo.",
  attributes:{classe:"Druido",livello:2,azione:"Azione",utilizzi_per_riposo:2,
   recupero_utilizzi:"Riposo breve o lungo",limiti_forma_selvatica:[
   {livello:2,gs_max:"1/4"},{livello:4,gs_max:"1/2"},{livello:8,gs_max:"1"}]}}},
 {title:"Nome lungo",card:{type:"feature",name:"Maestria Arcana della Trasmutazione Superiore",
  description:"Il privilegio permette di combinare più effetti sotto determinate condizioni.",
  attributes:{classe_genitore:"Mago",livello:14,tipo_attivazione:"Azione bonus",
   utilizzi_disponibili:"Bonus competenza",recupero:"Riposo lungo"}}},
 {title:"Descrizione lunga",card:{type:"feature",name:"Capacità di Prova",
  description:Array(7).fill("Un personaggio può usare questa capacità per effettuare una prova che influenza gli avversari vicini e determina una conseguenza.").join(" "),
  attributes:{classe:"Guerriero",livello:10,tipo_attivazione:"Reazione",
   utilizzi:"Una volta per riposo lungo",ricarica:"Alla fine di un riposo lungo",
   progressione:"Al 15° livello un utilizzo aggiuntivo."}}},
 {title:"Dati mancanti",card:{type:"feature",name:"Tratto Passivo",
  description:"Il privilegio conferisce un beneficio permanente.",
  attributes:{classe:"Ranger",livello:3}}},
];
export default function FeatureCardPreview(){
 const [index,setIndex]=React.useState(0);
 const [progression,setProgression]=React.useState(true);
 const entry=PREVIEWS[index];
 const card=React.useMemo(()=>{
  if(progression)return entry.card;
  const {progressione,miglioramenti,limiti_forma_selvatica,...rest}=entry.card.attributes||{};
  return {...entry.card,attributes:rest};
 },[entry,progression]);
 return <main className="min-h-screen bg-obsidian text-gold px-3 py-6 sm:py-10"
  data-testid="feature-card-preview">
  <div className="mx-auto max-w-2xl text-center">
   <h1 className="text-2xl font-display">TomoForge · Privilegi di classe</h1>
   <p className="mt-2 mb-4 text-xs text-foreground/70">
    Anteprima di prova separata · nessun login, nessun salvataggio e nessun merge.
   </p>
   <nav className="flex gap-2 justify-center flex-wrap mb-4" aria-label="Esempi di prova">
    {PREVIEWS.map((entry,i)=><button type="button" key={entry.title}
     onClick={()=>setIndex(i)} aria-pressed={i===index}
     className={"border border-gold-deep rounded px-2 py-1 text-xs "+(i===index?"bg-gold text-obsidian":"text-gold")}>
     {entry.title}
    </button>)}
   </nav>
   <div className="mx-auto" style={{width:"min(100%,360px)",aspectRatio:"5 / 7"}}>
    <CardFront card={card} editorMode />
   </div>
   <label className="mt-4 inline-flex gap-2 items-center text-xs">
    <input type="checkbox" checked={progression} onChange={e=>setProgression(e.target.checked)}/>
    Mostra progressione se presente
   </label>
   <p className="mt-3 text-xs text-foreground/60">Esempi dichiarati per il solo controllo grafico. I valori dell'app saranno letti dal record selezionato.</p>
  </div>
 </main>;
}
