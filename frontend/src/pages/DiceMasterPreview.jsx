import React from "react";
import { CardFront } from "@/components/TradingCard";
import { CLASS_HIT_DICE, classHitDieAsset } from "@/lib/classHitDice";

/** Public, read-only verification. No Supabase login and no record mutations. */
const DEMOS = {
  d4: ["Classe di prova", "Un dado vita d4 per verificare la variante grafica."],
  d6: ["Mago", "I maghi padroneggiano le arti arcane attraverso lo studio e la pratica."],
  d8: ["Druido", "I druidi custodiscono l'equilibrio delle forze naturali."],
  d10: ["Guerriero", "Maestri del combattimento, i guerrieri sono addestrati nell'uso di armi e armature e uniscono disciplina e resistenza per eccellere in battaglia."],
  d12: ["Barbaro", "I barbari affrontano il pericolo con vigore e forza straordinari."],
  d20: ["Classe di prova", "Un dado vita d20 per verificare la variante grafica."],
};

export default function DiceMasterPreview() {
  const [die, setDie] = React.useState("d10");
  const [name, description] = DEMOS[die];
  const card = {
    type: "class",
    name,
    description,
    attributes: {
      dado_vita: die,
      abilita_primaria: die === "d6" ? "Intelligenza" : "Forza o Destrezza",
      tiri_salvezza: "Forza, Costituzione",
      competenze: "Armature, scudi e armi",
    },
  };
  return (
    <main className="min-h-screen bg-obsidian text-gold px-3 py-8 text-center" data-testid="dice-preview-v29">
      <p className="font-label text-xs tracking-[.22em]">TOMO FORGE · ANTEPRIMA V29</p>
      <h1 className="font-display text-2xl sm:text-3xl mt-4">Dadi vita premium</h1>
      <p className="font-body text-sm max-w-lg mx-auto mt-3 text-foreground/75">
        Prova grafica reale con il componente carta dell'app. Nessun login richiesto, nessun record modificato.
        Il dado si aggiorna in base all'attributo della Classe.
      </p>
      <div className="flex flex-wrap justify-center gap-2 my-6" aria-label="Seleziona dado vita">
        {CLASS_HIT_DICE.map(d => (
          <button key={d} type="button" onClick={() => setDie(d)}
            aria-pressed={die === d}
            className={`px-3 py-2 min-w-12 font-label border ${die === d ? "bg-gold text-obsidian border-gold" : "border-gold-deep text-gold"}`}>
            {d}
          </button>
        ))}
      </div>
      <div className="mx-auto" style={{ width: 280, aspectRatio: "2.5 / 3.5" }}>
        <CardFront card={card} editorMode />
      </div>
      <p className="font-body text-sm text-foreground/70 my-6">
        Dado selezionato: <strong>{die}</strong> · Master originale della seconda immagine.
      </p>
      <div className="mx-auto grid grid-cols-3 sm:grid-cols-6 gap-1 max-w-3xl">
        {CLASS_HIT_DICE.map(d => (
          <button type="button" key={d} onClick={() => setDie(d)}
            aria-label={`Mostra ${d}`} className="p-1 border border-gold-deep/30">
            <img src={classHitDieAsset(d)} alt={d} width="120" height="125" className="w-full h-auto" />
          </button>
        ))}
      </div>
      <p className="font-body text-xs text-foreground/60 mt-5">
        Questa anteprima è separata dalla produzione finché il nuovo fronte non è approvato.
      </p>
    </main>
  );
}
