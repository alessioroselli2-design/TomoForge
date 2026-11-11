import React from "react";
import { CardFront } from "@/components/TradingCard";

/**
 * Preview on the *real* CardFront renderer, isolated from production records.
 * Only sample data is used. This page never calls the API or saves edits.
 */
export const CLASS_PREVIEW_FIXTURES = [
  {name:"Barbaro",die:"d12",primary:"Forza",saves:"Forza, Costituzione",proficiencies:"Armature leggere, medie, scudi, armi semplici e da guerra",description:"I barbari sono guerrieri indomiti che attingono alla propria rabbia per affrontare ogni pericolo. La loro forza straordinaria, la resistenza e gli istinti primordiali li rendono combattenti formidabili, capaci di proteggere gli alleati anche nelle battaglie più feroci."},
  {name:"Bardo",die:"d8",primary:"Carisma",saves:"Destrezza, Carisma",proficiencies:"Armature leggere, armi semplici, balestre a mano, spade corte, spade lunghe, stocchi",description:"Artisti e musici intrisi di magia, i bardi intrecciano melodia, parola e incanto per ispirare gli alleati, confondere i nemici e plasmare la realtà con il potere della loro arte. Viaggiatori, narratori e depositari di mille storie, portano ovunque la forza dell'immaginazione."},
  {name:"Chierico",die:"d8",primary:"Saggezza",saves:"Saggezza, Carisma",proficiencies:"Armature leggere, medie, scudi e armi semplici",description:"I chierici sono devoti servitori di una divinità, incaricati di diffondere la sua volontà nel mondo. Attraverso la fede, canalizzano il potere divino per guarire, proteggere gli alleati e scacciare le forze del male."},
  {name:"Druido",die:"d8",primary:"Saggezza",saves:"Intelligenza, Saggezza",proficiencies:"Armature leggere, medie, scudi, clave, pugnali, dardi, giavellotti, mazze, bastoni ferrati, falcetti",description:"I druidi sono i custodi della natura, mediatori tra il mondo civilizzato e la forza primordiale della vita. Attingono al potere delle foreste, degli animali e degli elementi per proteggere l'equilibrio del mondo, curare, plasmare la natura e scatenare la sua ira contro chi la minaccia."},
  {name:"Guerriero",die:"d10",primary:"Forza o Destrezza",saves:"Forza, Costituzione",proficiencies:"Tutte le armature, scudi, armi semplici e da guerra",description:"I guerrieri sono maestri del combattimento, addestrati nell'uso delle armi e delle armature. Uniscono disciplina, forza, strategia e resistenza per affrontare le sfide più pericolose, difendendo i propri compagni e distinguendosi in battaglia."},
  {name:"Monaco",die:"d8",primary:"Destrezza e Saggezza",saves:"Forza, Destrezza",proficiencies:"Armi semplici, spade corte",description:"I monaci affinano corpo e spirito attraverso la disciplina, l'equilibrio e il controllo dell'energia interiore. Con mente lucida e movimenti precisi, trasformano la forza della volontà in potenza, armonia e protezione per sé e per gli altri."},
  {name:"Paladino",die:"d10",primary:"Forza e Carisma",saves:"Saggezza, Carisma",proficiencies:"Tutte le armature, scudi, armi semplici e da guerra",description:"I paladini sono campioni del sacro, guerrieri di luce che uniscono la forza delle armi alla potenza della fede. Legati da solenni giuramenti, difendono i deboli, combattono le tenebre e portano la giustizia laddove regna l'ingiustizia."},
  {name:"Ranger",die:"d10",primary:"Destrezza e Saggezza",saves:"Forza, Destrezza",proficiencies:"Armature leggere e medie, scudi, armi semplici e da guerra",description:"I ranger sono esploratori e cacciatori delle terre selvagge, maestri di natura, tracciare e sopravvivenza. Si muovono con discrezione tra foreste, montagne e rovine dimenticate, proteggendo l'equilibrio del mondo selvatico e affrontando le minacce che lo insidiano."},
  {name:"Ladro",die:"d8",primary:"Destrezza",saves:"Destrezza, Intelligenza",proficiencies:"Armature leggere, armi semplici, balestre a mano, spade lunghe, stocchi, spade corte, arnesi da scasso",description:"I ladri sono maestri di furtività, precisione e opportunità. Si muovono nell'ombra, colpiscono con rapidità e sfruttano ogni vantaggio, trasformando la discrezione, l'astuzia e l'agilità in armi letali quanto efficaci."},
  {name:"Stregone",die:"d6",primary:"Carisma",saves:"Costituzione, Carisma",proficiencies:"Pugnali, dardi, fionde, bastoni ferrati, balestre leggere",description:"Gli stregoni maneggiano un potere arcano innato che scorre nelle loro vene come un'eredità misteriosa. Non studiano la magia: la incarnano, plasmandola con istinto, volontà ed emozione, sprigionando effetti straordinari con un solo gesto."},
  {name:"Warlock",die:"d8",primary:"Carisma",saves:"Saggezza, Carisma",proficiencies:"Armature leggere e armi semplici",description:"I Warlock ottengono un potere proibito attraverso un patto con un'entità sovrannaturale, scambiando parte della propria libertà per doni arcani straordinari. Guidati da forze antiche e misteriose, manipolano energie oscure, segreti e poteri che vanno oltre i confini della magia comune."},
  {name:"Mago",die:"d6",primary:"Intelligenza",saves:"Intelligenza, Saggezza",proficiencies:"Pugnali, dardi, fionde, bastoni ferrati, balestre leggere",description:"I maghi dedicano la vita allo studio dei segreti dell'arcano. Attraverso grimori, formule e rituali, trasformano la conoscenza in potere, manipolando le forze della magia per proteggere gli alleati e affrontare le minacce più temibili."},
  {name:"Artefice",die:"d8",primary:"Intelligenza",saves:"Costituzione, Intelligenza",proficiencies:"Armature leggere, medie, scudi, armi semplici",description:"Gli artefici coniugano ingegno, magia e invenzione incantata, trasformando idee brillanti in strumenti straordinari. Attraverso la conoscenza, la creatività e l'arte della costruzione, plasmano oggetti magici che potenziano sé stessi e i propri alleati."},
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
