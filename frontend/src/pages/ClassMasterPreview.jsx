import React from "react";
import { CardFront } from "@/components/TradingCard";

/**
 * Preview on the *real* CardFront renderer, isolated from production records.
 * Only sample data is used. This page never calls the API or saves edits.
 */
export const CLASS_PREVIEW_FIXTURES = [
  {name:"Barbaro",die:"d12",primary:"Forza",saves:"Forza, Costituzione",proficiencies:"Armature leggere, medie, scudi, armi semplici e da guerra",description:"I barbari fanno della rabbia e della forza straordinaria le loro armi principali."},
  {name:"Bardo",die:"d8",primary:"Carisma",saves:"Destrezza, Carisma",proficiencies:"Armature leggere, armi semplici, balestre a mano, spade corte, spade lunghe, stocchi",description:"Artisti e musici intrisi di magia, i bardi intrecciano melodia, parola e incanto per ispirare gli alleati."},
  {name:"Chierico",die:"d8",primary:"Saggezza",saves:"Saggezza, Carisma",proficiencies:"Armature leggere, medie, scudi e armi semplici",description:"I chierici sono devoti servitori di una divinità e canalizzano il potere divino per guarire e proteggere gli alleati."},
  {name:"Druido",die:"d8",primary:"Saggezza",saves:"Intelligenza, Saggezza",proficiencies:"Armature leggere, medie, scudi, clave, pugnali, dardi, giavellotti, mazze, bastoni ferrati, falcetti",description:"I druidi sono custodi della natura e attingono alle forze primordiali del mondo."},
  {name:"Guerriero",die:"d10",primary:"Forza o Destrezza",saves:"Forza, Costituzione",proficiencies:"Tutte le armature, scudi, armi semplici e da guerra",description:"Maestri del combattimento, i guerrieri uniscono addestramento, disciplina e resistenza per eccellere in battaglia."},
  {name:"Monaco",die:"d8",primary:"Destrezza e Saggezza",saves:"Forza, Destrezza",proficiencies:"Armi semplici, spade corte",description:"I monaci affinano corpo e spirito attraverso disciplina e controllo dell'energia interiore."},
  {name:"Paladino",die:"d10",primary:"Forza e Carisma",saves:"Saggezza, Carisma",proficiencies:"Tutte le armature, scudi, armi semplici e da guerra",description:"I paladini sono campioni del sacro, legati a solenni giuramenti e impegnati nella difesa dei deboli."},
  {name:"Ranger",die:"d10",primary:"Destrezza e Saggezza",saves:"Forza, Destrezza",proficiencies:"Armature leggere e medie, scudi, armi semplici e da guerra",description:"I ranger sono esploratori delle terre selvagge, maestri di tracce, natura e sopravvivenza."},
  {name:"Ladro",die:"d8",primary:"Destrezza",saves:"Destrezza, Intelligenza",proficiencies:"Armature leggere, armi semplici, balestre a mano, spade lunghe, stocchi, spade corte, arnesi da scasso",description:"I ladri sono maestri di furtività, precisione e opportunità, capaci di trasformare ogni vantaggio in un colpo decisivo."},
  {name:"Stregone",die:"d6",primary:"Carisma",saves:"Costituzione, Carisma",proficiencies:"Pugnali, dardi, fionde, bastoni ferrati, balestre leggere",description:"Gli stregoni maneggiano un potere arcano innato, che scorre nelle loro vene come un'eredità misteriosa."},
  {name:"Warlock",die:"d8",primary:"Carisma",saves:"Saggezza, Carisma",proficiencies:"Armature leggere e armi semplici",description:"I warlock ottengono conoscenze arcane e poteri straordinari attraverso un patto con un'entità sovrannaturale."},
  {name:"Mago",die:"d6",primary:"Intelligenza",saves:"Intelligenza, Saggezza",proficiencies:"Pugnali, dardi, fionde, bastoni ferrati, balestre leggere",description:"Gli studiosi della magia arcana cercano di padroneggiare i segreti dell'universo tramite studio e disciplina."},
  {name:"Artefice",die:"d8",primary:"Intelligenza",saves:"Costituzione, Intelligenza",proficiencies:"Armature leggere, medie, scudi, armi semplici",description:"Gli artefici coniugano ingegno, magia e invenzione incantata per creare straordinari oggetti magici."},
];

const makeDemoCard = (sample) => ({
  type:"class",
  name:sample.name,
  description:sample.description,
  attributes:{
    dado_vita:sample.die,
    abilita_primaria:sample.primary,
    tiri_salvezza:sample.saves,
    competenze:sample.proficiencies,
  },
});

export default function ClassMasterPreview() {
  const [selected,setSelected] = React.useState("Bardo");
  const [artwork,setArtwork] = React.useState(null);
  const [previewUrl,setPreviewUrl] = React.useState("");
  const [approvedReference,setApprovedReference] = React.useState(null);
  const [referenceUrl,setReferenceUrl] = React.useState("");
  const fileInput=React.useRef(null);
  const referenceInput=React.useRef(null);
  const sample=CLASS_PREVIEW_FIXTURES.find(item=>item.name===selected)||CLASS_PREVIEW_FIXTURES[0];
  const card=React.useMemo(()=>makeDemoCard(sample),[sample]);

  React.useEffect(()=>{
    if(!artwork){setPreviewUrl("");return undefined;}
    const url=URL.createObjectURL(artwork);
    setPreviewUrl(url);
    return ()=>URL.revokeObjectURL(url);
  },[artwork]);

  React.useEffect(()=>{
    if(!approvedReference){setReferenceUrl("");return undefined;}
    const url=URL.createObjectURL(approvedReference);
    setReferenceUrl(url);
    return ()=>URL.revokeObjectURL(url);
  },[approvedReference]);

  const onChooseClass=(name)=>{
    setSelected(name);
    setArtwork(null);
    setApprovedReference(null);
    if(fileInput.current)fileInput.current.value="";
    if(referenceInput.current)referenceInput.current.value="";
  };

  return (
    <main className="min-h-screen bg-obsidian text-gold px-3 py-7 sm:py-10" data-testid="class-master-preview">
      <div className="mx-auto max-w-5xl text-center">
        <p className="font-label text-xs tracking-[.19em]">TOMO FORGE · COLLAUDO GRAFICO</p>
        <h1 className="font-display text-2xl sm:text-3xl mt-3">Prova fronte Classi</h1>
        <p className="font-body text-sm text-foreground/80 mt-3 max-w-2xl mx-auto">
          Questa è la vera carta renderizzata da TomoForge: simboli, caselle e dado
          vengono scelti dalla classe. La cornice non cambia e l'illustrazione
          rimane vuota finché non ne selezioni una.
        </p>
        <p className="font-body text-xs mt-2 text-foreground/60">
          Dati dimostrativi per verificare il layout · nessun login, salvataggio o modifica ai record
        </p>
        <nav className="flex flex-wrap justify-center gap-2 mt-6" aria-label="Classe da verificare">
          {CLASS_PREVIEW_FIXTURES.map(item=>(
            <button type="button" key={item.name} aria-pressed={selected===item.name}
              onClick={()=>onChooseClass(item.name)}
              className={selected===item.name
                ?"px-3 py-2 rounded border border-gold bg-gold text-obsidian text-sm font-label"
                :"px-3 py-2 rounded border border-gold/50 text-gold text-sm font-label"}>
              {item.name}
            </button>
          ))}
        </nav>
        <div className="flex flex-wrap gap-3 justify-center items-center my-6">
          <label className="cursor-pointer px-4 py-2 border border-gold/70 rounded text-sm font-label">
            Prova una tua illustrazione
            <input ref={fileInput} type="file" accept="image/*" className="sr-only"
              onChange={e=>setArtwork(e.target.files?.[0]||null)}/>
          </label>
          <label className="cursor-pointer px-4 py-2 border border-gold/70 rounded text-sm font-label">
            Confronta con la carta approvata
            <input ref={referenceInput} type="file" accept="image/*" className="sr-only"
              onChange={e=>setApprovedReference(e.target.files?.[0]||null)}/>
          </label>
          {artwork&&<button type="button" className="text-sm underline" onClick={()=>{
            setArtwork(null);
            if(fileInput.current)fileInput.current.value="";
          }}>Svuota l'immagine</button>}
        </div>
        <div className="flex flex-col items-center gap-3">
          <p className="font-label text-sm">{selected} · dado vita {sample.die}</p>
          <div style={{width:"min(94vw, 440px)",aspectRatio:"2.5 / 3.5"}}>
            <CardFront key={selected} card={card} imgUrl={previewUrl||undefined} />
          </div>
        </div>
        {referenceUrl&&<div className="mt-8 mx-auto w-full max-w-lg text-center">
          <h2 className="font-display text-lg mb-2">Immagine approvata · confronto locale</h2>
          <img src={referenceUrl} alt={`Riferimento approvato per ${selected}`}
            className="mx-auto w-full max-w-sm h-auto object-contain" />
          <p className="font-body text-xs text-foreground/60 mt-2">Il riferimento rimane solo nel tuo dispositivo, non viene caricato sul server.</p>
        </div>}
        <p className="font-body text-xs text-foreground/65 max-w-xl mx-auto mt-7">
          Prova isolata del master dell'app: le immagini delle schede approvate restano
          il riferimento visivo. L'anteprima non aggiorna Supabase e non pubblica carte.
        </p>
      </div>
    </main>
  );
}
