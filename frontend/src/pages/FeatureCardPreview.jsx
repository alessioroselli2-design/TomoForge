import React from "react";
import { CardFront } from "@/components/TradingCard";

const FORMA_SELVATICA={
 type:"feature",name:"Forma Selvatica",
 description:"Come azione, puoi trasformarti in una bestia che conosci e che abbia un grado di sfida pari o inferiore a 1/4. Mantieni i tuoi punti ferita e puoi tornare alla tua forma normale come azione bonus.",
 attributes:{
  classe:"Druido",livello:"2",tipo_attivazione:"Azione",
  utilizzi_disponibili:"2",recupero_utilizzi:"Riposo breve o lungo",
  progressione:"Il limite del grado di sfida aumenta ai livelli successivi.",
 }
};
const icons=[
 ["Attivazione","/card-art/feature-icons/attivazione.svg"],
 ["Utilizzi disponibili","/card-art/feature-icons/utilizzi.svg"],
 ["Recupero degli utilizzi","/card-art/feature-icons/recupero.svg"],
];
export default function FeatureCardPreview(){
 const [withProgression,setWithProgression]=React.useState(true);
 const card=React.useMemo(()=>({...FORMA_SELVATICA,attributes:{
  ...FORMA_SELVATICA.attributes,
  progressione:withProgression?FORMA_SELVATICA.attributes.progressione:"",
 }}),[withProgression]);
 return <main className="min-h-screen bg-obsidian text-gold px-3 py-6 sm:py-10"
  data-testid="feature-card-preview">
   <div className="mx-auto max-w-xl text-center">
    <h1 className="text-2xl font-display">TomoForge · Prova Privilegi</h1>
    <p className="text-sm text-foreground/75 mt-2 mb-4">
      Anteprima dedicata senza login e senza merge. È il renderer reale del ramo di prova.
    </p>
    <section className="grid grid-cols-3 gap-2 mb-5" aria-label="Simboli dei privilegi">
      {icons.map(([label,src])=><div key={label} className="flex flex-col items-center gap-1 border border-gold-deep/40 rounded p-2">
        <img src={src} alt={label} className="h-12 w-12 object-contain"/>
        <span className="text-xs text-foreground/85">{label}</span>
      </div>)}
    </section>
    <div className="mx-auto" style={{width:"min(100%,360px)",aspectRatio:"5 / 7"}}>
      <CardFront card={card} editorMode />
    </div>
    <label className="mt-5 flex gap-2 justify-center items-center text-sm">
      <input type="checkbox" checked={withProgression}
        onChange={e=>setWithProgression(e.target.checked)}/>
      Mostra testo della progressione
    </label>
    <p className="mt-4 text-xs text-foreground/70">
      Forma Selvatica: valori di esempio per il solo controllo grafico, non record della biblioteca.
      Senza progressione la fascia resta vuota. Nessuna modifica alla produzione.
    </p>
   </div>
 </main>;
}
