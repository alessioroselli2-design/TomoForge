import React from "react";
import { CardFront } from "@/components/TradingCard";
import { api } from "@/lib/api";

// Demo fixtures are deliberately separate from authenticated library records.
// They are never presented as genuine saving throws, competences or descriptions.
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

const normalize = value => String(value || "").normalize("NFD")
  .replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9 ]/g," ").trim();
const alias = {esploratore:"ranger",artificiere:"artefice",occultista:"warlock"};
const classKey = value => alias[normalize(value)] || normalize(value);

export default function ClassAbilityPreview() {
  const [index,setIndex] = React.useState(4); // Open the reported Warrior regression first
  const [mode,setMode] = React.useState("real");
  const [status,setStatus] = React.useState("loading");
  const [sourceRecords,setSourceRecords] = React.useState([]);
  const [error,setError] = React.useState("");

  const loadActualRecords = React.useCallback(async () => {
    setStatus("loading");setError("");
    try {
      const {data} = await api.get("/library/class-preview-records");
      const records = Array.isArray(data?.records) ? data.records : [];
      setSourceRecords(records);
      setStatus(records.length ? "loaded" : "empty");
      setMode("real");
    } catch(err) {
      setStatus("unavailable");
      setError(err?.response?.status===401 || err?.response?.status===403
        ? "Dati reali protetti: accedi a TomoForge su questa anteprima per consultare la tua biblioteca."
        : "Dati reali non disponibili in questa anteprima. Non è stato modificato alcun record.");
      setMode("demo");
    }
  },[]);

  React.useEffect(() => {loadActualRecords();},[loadActualRecords]);
  const [demoName,demoAbility,demoDie]=CLASSES[index];
  const realRecord=sourceRecords.find(record=>classKey(record.name)===classKey(demoName));
  const card=mode==="real" ? realRecord : {
    type:"class",name:demoName,
    description:"", // never forge a real class description
    attributes:{
      dado_vita:demoDie,abilita_primaria:demoAbility,
      tiri_salvezza:"",competenze:"",
    },
  };
  const attrs=realRecord?.attributes || {};
  const display=(field,fallback="Non presente nel record") => String(attrs[field]||fallback);
  return <main className="min-h-screen bg-obsidian text-gold px-3 py-8" data-testid="class-abilities-preview">
    <div className="mx-auto max-w-4xl">
      <h1 className="font-display text-2xl text-center">TomoForge · Collaudo Classi</h1>
      <p className="text-center text-sm mt-2 mb-3 text-foreground/75">
        Renderer reale · ramo di prova · nessuna modifica alla biblioteca
      </p>
      <div className="border border-gold-deep/40 rounded p-3 mb-4 text-center text-sm">
        {status==="loading"&&<p>Ricerca dei record autenticati nella biblioteca…</p>}
        {status==="loaded"&&<p>{sourceRecords.length} record di Classe verificati disponibili in sola lettura.</p>}
        {status==="empty"&&<p>La biblioteca autenticata non contiene record di Classe verificati.</p>}
        {status==="unavailable"&&<p role="alert">{error}</p>}
        <div className="flex flex-wrap justify-center gap-2 mt-3">
          <button type="button" onClick={loadActualRecords} className="border border-gold px-3 py-2 rounded">
            Riprova dati reali
          </button>
          <button type="button" onClick={()=>setMode("demo")} aria-pressed={mode==="demo"} className="border border-gold px-3 py-2 rounded">
            Solo prova grafica
          </button>
          {sourceRecords.length>0&&<button type="button" onClick={()=>setMode("real")} aria-pressed={mode==="real"}
            className="border border-gold px-3 py-2 rounded">Usa i record reali</button>}
        </div>
      </div>
      <p className="mb-3 text-center text-xs text-foreground/70">
        Modalità: {mode==="real"?"record realmente presenti nella biblioteca":"esempio grafico (nessuna descrizione o competenza inventata)"}
      </p>
      <div className="flex flex-wrap justify-center gap-2 mb-5">
        {CLASSES.map(([label],i)=><button key={label} type="button"
          onClick={()=>setIndex(i)} aria-pressed={index===i}
          className={`border rounded px-3 py-2 text-sm ${index===i?"bg-gold text-obsidian border-gold":"border-gold-deep text-gold"}`}>
          {label}
        </button>)}
      </div>
      <p className="text-center mb-4 text-sm">
        {demoName} · {mode==="real"?(realRecord?"Dati verificati":"Record verificato non trovato"):"Sola verifica grafica"}
      </p>
      {card ? <>
        <div className="mx-auto" style={{width:320,aspectRatio:"2.5 / 3.5"}}>
          <CardFront card={card} editorMode />
        </div>
        {mode==="real"&&<section className="mt-6 border border-gold-deep/30 rounded p-4 text-sm">
          <h2 className="font-semibold mb-2">Valori originali del record</h2>
          <p><strong>Abilità Primaria:</strong> {display("abilita_primaria")}</p>
          <p><strong>Tiri Salvezza:</strong> {display("tiri_salvezza")}</p>
          <p><strong>Competenze:</strong> {display("competenze")}</p>
          <p className="mt-2"><strong>Descrizione reale:</strong> {realRecord.description || "Descrizione non presente"}</p>
        </section>}
      </> : <p className="text-center border border-gold-deep/30 rounded p-4">
        Nessun record verificato per {demoName}. Scegli «Solo prova grafica» per controllare esclusivamente i simboli.
      </p>}
      <p className="text-center text-xs text-foreground/60 mt-5">
        La lettura non chiama API di applicazione, importazione, revisione o salvataggio.
      </p>
    </div>
  </main>;
}
