import React from "react";
import { CardFront } from "@/components/TradingCard";
import { renderCardCanvas } from "@/lib/cardExport";
import { CLASS_HIT_DICE, classHitDieAsset } from "@/lib/classHitDice";

/** Public, read-only verification. No Supabase login and no record mutations. */
const DEMOS = {
  d4: ["Classe di prova", "Un dado vita d4 per verificare la variante grafica."],
  d6: ["Mago", "I maghi padroneggiano le arti arcane attraverso lo studio e la pratica."],
  d8: ["Druido", "I druidi custodiscono l'equilibrio delle forze naturali."],
  d10: ["Guerriero", "Maestri del combattimento. Tutti conoscono bene la morte, sia perché la elargiscono, sia perché spesso la incontrano sul campo di battaglia. I guerrieri sono addestrati all'uso di un'ampia varietà di armi e armature. Uniscono addestramento, disciplina e resistenza per eccellere in battaglia."],
  d12: ["Barbaro", "I barbari affrontano il pericolo con vigore e forza straordinari."],
  d20: ["Classe di prova", "Un dado vita d20 per verificare la variante grafica."],
};

export default function DiceMasterPreview() {
  const spellModeFromUrl = new URLSearchParams(window.location.search).get("tipo") === "incantesimo";
  const [mode, setMode] = React.useState(spellModeFromUrl ? "spell" : "class");
  const [die, setDie] = React.useState(spellModeFromUrl ? "d6" : "d10");
  const frontRef = React.useRef(null);
  const [printPreview,setPrintPreview] = React.useState("");
  const [printError,setPrintError] = React.useState("");

  const [name, description] = DEMOS[die];
  // Public, read-only layout stress test: a multi-paragraph narrative as long
  // as a real imported Class. The card remains a STATIC printable artifact.
  const stress = new URLSearchParams(window.location.search).get("stress") === "1";
  const longDescription = [
    "Un'umana in una sferragliante corazza di piastre solleva lo scudo davanti a sé e si tuffa di corsa verso un gruppo di goblin. Un elfo alle sue spalle, protetto da un'armatura di cuoio borchiato, fa piovere la morte sui goblin scagliando una raffica di frecce con il suo arco di pregiata fattura.",
    "Al suo fianco, un mezzorco grida una serie di ordini per aiutare i due combattenti a coordinare il loro attacco. I guerrieri conoscono bene le armi e le armature.",
    "Una nuova battaglia li attende oltre le mura dell'antica fortezza. La loro determinazione è pari soltanto al coraggio.",
    "Nel corso delle loro imprese perfezionano la tecnica, la disciplina e la resistenza. La loro storia attraversa le generazioni."
  ].join(" ");

  // The demo now validates data changes too, not only the visual dice.
  const classDemoAttributes = ({
    d4:{abilita_primaria:"Destrezza",tiri_salvezza:"Destrezza, Intelligenza",competenze:"Armi semplici"},
    d6:{abilita_primaria:"Intelligenza",tiri_salvezza:"Intelligenza, Saggezza",competenze:"Pugnali, dardi, balestre leggere"},
    d8:{abilita_primaria:"Saggezza",tiri_salvezza:"Intelligenza, Saggezza",competenze:"Armature leggere, medie e scudi"},
    d10:{abilita_primaria:"Forza o Destrezza",tiri_salvezza:"Forza, Costituzione",competenze:"Tutte le armature, scudi, armi semplici e da guerra"},
    d12:{abilita_primaria:"Forza",tiri_salvezza:"Forza, Costituzione",competenze:"Armature leggere, medie, scudi, armi semplici e da guerra"},
    d20:{abilita_primaria:"Forza",tiri_salvezza:"Forza, Costituzione",competenze:"Armi da guerra"}
  })[die];
  const spellFormula = ({d4:"1d4+1",d6:"8d6",d8:"3d8",d10:"2d10+3",d12:"1d12",d20:"1d20"})[die];
  const card = mode === "spell" ? {
    type:"spell", name:die==="d6"?"Palla di Fuoco":"Incantesimo dimostrativo",
    description:"Prova grafica della formula reale, con lo stesso dado illustrato delle Classi.",
    attributes:{livello:"3",scuola:"Invocazione",tempo_lancio:"1 azione",gittata:"45 m",danno:spellFormula+" fuoco"}
  } : {
    type:"class",name,description:stress?longDescription:description,
    attributes:{dado_vita:die,...classDemoAttributes},
  };
  const verifyPrintedClass=async()=>{
    try{
      setPrintError("");
      const canvas=await renderCardCanvas(frontRef.current,card);
      setPrintPreview(canvas.toDataURL("image/png"));
    }catch(error){
      setPrintPreview("");
      setPrintError(String(error?.message||error));
    }
  };
  return (
    <main className="min-h-screen bg-obsidian text-gold px-3 py-8 text-center" data-testid="dice-preview-v29">
      <p className="font-label text-xs tracking-[.22em]">TOMO FORGE · ANTEPRIMA V29</p>
      <h1 className="font-display text-2xl sm:text-3xl mt-4">Dadi premium · Classi e Incantesimi</h1>
      <p className="font-body text-sm max-w-lg mx-auto mt-3 text-foreground/75">
        Prova sulla vera carta TomoForge, senza login e senza modificare alcun record.
        Per gli incantesimi la formula completa compare dentro la gemma, come Palla di Fuoco.
      </p>
      <div className="flex justify-center gap-3 mt-6">
        <button type="button" onClick={()=>setMode("class")} aria-pressed={mode==="class"}
          className={`border px-4 py-2 ${mode==="class"?"bg-gold text-obsidian":"border-gold text-gold"}`}>Classi</button>
        <button type="button" onClick={()=>setMode("spell")} aria-pressed={mode==="spell"}
          className={`border px-4 py-2 ${mode==="spell"?"bg-gold text-obsidian":"border-gold text-gold"}`}>Incantesimi</button>
      </div>
      <div className="flex flex-wrap justify-center gap-2 my-6" aria-label="Seleziona dado">
        {CLASS_HIT_DICE.map(d => (
          <button key={d} type="button" onClick={() => setDie(d)}
            aria-pressed={die === d}
            className={`px-3 py-2 min-w-12 font-label border ${die === d ? "bg-gold text-obsidian border-gold" : "border-gold-deep text-gold"}`}>
            {d}
          </button>
        ))}
      </div>
      <div className="mx-auto" style={{ width: 280, aspectRatio: "2.5 / 3.5" }}>
        <CardFront ref={frontRef} card={card} editorMode />
      </div>
      {mode==="class"&&<div className="mx-auto my-5 max-w-xs">
        <button type="button" onClick={verifyPrintedClass}
          className="w-full border border-gold-deep px-4 py-2 text-gold font-label"
          data-testid="check-class-print">Verifica versione PNG da stampa</button>
        {printError&&<p role="alert" className="mt-2 text-red-300 text-sm">{printError}</p>}
        {printPreview&&<img src={printPreview} alt="Anteprima PNG da stampa della classe"
          data-testid="class-export-preview" className="mt-3 w-full h-auto" />}
      </div>}
      {/* Formula already appears inside the medallion: do not repeat it below the card. */}
      <div className="mx-auto grid grid-cols-3 sm:grid-cols-6 gap-1 max-w-3xl">
        {CLASS_HIT_DICE.map(d => (
          <button type="button" key={d} onClick={() => setDie(d)}
            aria-label={`Mostra ${d}`} className="p-1 border border-gold-deep/30">
            <img src={classHitDieAsset(d)} alt={d} width="120" height="125" className="w-full h-auto" />
          </button>
        ))}
      </div>
      <p className="font-body text-xs text-foreground/60 mt-5">
        Pagina di collaudo grafico: nessun record viene modificato.
      </p>
    </main>
  );
}
