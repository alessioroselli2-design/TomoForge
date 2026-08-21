import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, BookOpen, FileText, Loader2, Pencil, Printer, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import Navbar from "@/components/Navbar";
import { Button } from "@/components/ui/button";

const ABILITIES = [
  ["for", "FOR", "Forza"],
  ["des", "DES", "Destrezza"],
  ["cos", "COS", "Costituzione"],
  ["int", "INT", "Intelligenza"],
  ["sag", "SAG", "Saggezza"],
  ["car", "CAR", "Carisma"],
];

const asList = (value) => {
  if (Array.isArray(value)) return value.filter(Boolean);
  if (typeof value !== "string") return [];
  return value.split(/\n|,/).map((item) => item.trim()).filter(Boolean);
};

const asScore = (value) => {
  const match = String(value ?? "").match(/-?\d+/);
  return match ? Number(match[0]) : null;
};

const formatMod = (value) => {
  const score = asScore(value);
  if (score === null) return "—";
  const mod = Math.floor((score - 10) / 2);
  return `${mod >= 0 ? "+" : ""}${mod}`;
};

const derivedProficiency = (level) => {
  const parsed = asScore(level);
  return parsed && parsed > 0 ? `+${2 + Math.floor((Math.min(parsed, 20) - 1) / 4)}` : "—";
};

const hasValue = (value) => {
  if (Array.isArray(value)) return value.length > 0;
  return value !== undefined && value !== null && String(value).trim() !== "";
};

const copyIfMissing = (target, key, value) => {
  if (!hasValue(target[key]) && hasValue(value)) target[key] = value;
};

const manualDefaults = (records, attributes) => {
  const next = { ...attributes };
  records.forEach((record) => {
    const source = record.attributes || {};
    if (record.reference_type === "class") {
      copyIfMissing(next, "dadi_vita", source.dado_vita);
      copyIfMissing(next, "competenze", source.competenze);
      copyIfMissing(next, "tiri_salvezza", source.tiri_salvezza);
    }
    if (record.reference_type === "race" || record.reference_type === "subrace") {
      copyIfMissing(next, "velocita", source.velocita);
      copyIfMissing(next, "linguaggi", source.linguaggi);
      copyIfMissing(next, "tratti_razza", source.tratti);
    }
    if (record.reference_type === "subclass") {
      copyIfMissing(next, "abilita_sottoclasse", source.caratteristiche || source.privilegi);
    }
  });
  return next;
};

const ValueList = ({ title, values, empty = "Nessun dato inserito." }) => (
  <section className="border border-gold-deep/45 bg-card/75 p-5">
    <h2 className="font-label text-xs tracking-[0.18em] text-gold">{title}</h2>
    {values.length ? (
      <ul className="mt-3 space-y-2">
        {values.map((item, index) => (
          <li key={`${String(item)}-${index}`} className="border-l-2 border-gold-deep/60 pl-3 font-body text-sm leading-relaxed text-foreground/90">
            {typeof item === "object"
              ? <><strong className="text-gold">{item.nome || item.name || "Voce"}</strong>{item.descrizione || item.description ? ` — ${item.descrizione || item.description}` : ""}</>
              : item}
          </li>
        ))}
      </ul>
    ) : <p className="mt-3 font-body text-sm text-muted-foreground">{empty}</p>}
  </section>
);

export default function CharacterSheet() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [card, setCard] = useState(null);
  const [linkedRecords, setLinkedRecords] = useState([]);
  const [loadingLinks, setLoadingLinks] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [libraryNotice, setLibraryNotice] = useState("");

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/cards/${id}`);
      if (data.type !== "character") {
        toast.error("Questa carta non è un personaggio");
        navigate(`/carta/${id}`, { replace: true });
        return;
      }
      setCard(data);
    } catch (error) {
      toast.error("Personaggio non trovato");
      navigate("/collezione", { replace: true });
    }
  }, [id, navigate]);

  useEffect(() => { load(); }, [load]);

  const attributes = card?.attributes || {};
  const lookups = useMemo(() => [
    { query: attributes.classe, types: "class,subclass,class_feature" },
    { query: attributes.sottoclasse, types: "subclass,class_feature" },
    { query: attributes.razza, types: "race,subrace" },
    { query: attributes.sottorazza, types: "subrace" },
  ].filter((entry) => String(entry.query || "").trim()), [attributes.classe, attributes.sottoclasse, attributes.razza, attributes.sottorazza]);

  useEffect(() => {
    if (!card || !lookups.length) {
      setLinkedRecords([]);
      setLibraryNotice("");
      return;
    }
    let active = true;
    setLoadingLinks(true);
    Promise.all(lookups.map((entry) => api.get("/library", { params: { q: entry.query, types: entry.types } })))
      .then((responses) => {
        if (!active) return;
        const unique = new Map();
        responses.flatMap((response) => response.data.records || []).forEach((record) => unique.set(record.id, record));
        setLinkedRecords([...unique.values()].slice(0, 12));
        const unavailable = responses
          .filter((response) => response.data.status === "unavailable")
          .map((response) => response.data.message)
          .find(Boolean);
        setLibraryNotice(unavailable || "");
      })
      .catch(() => {
        if (active) {
          setLinkedRecords([]);
          setLibraryNotice("La biblioteca non è disponibile in questo momento: nessun dato è stato applicato.");
        }
      })
      .finally(() => { if (active) setLoadingLinks(false); });
    return () => { active = false; };
  }, [card, lookups]);

  if (!card) {
    return (
      <div className="min-h-screen bg-obsidian"><Navbar /><div className="flex justify-center py-32"><Loader2 className="h-6 w-6 animate-spin text-gold" /></div></div>
    );
  }

  const level = attributes.livello || "—";
  const proficiency = attributes.bonus_competenza || derivedProficiency(level);
  const identity = [
    attributes.razza, attributes.sottorazza, attributes.classe, attributes.sottoclasse,
  ].filter(Boolean).join(" · ");
  const capabilities = [...asList(attributes.abilita_sottoclasse), ...asList(attributes.privilegi)];
  const sourceRecords = linkedRecords.filter((record) => record.source_refs?.length);

  const completeFromManuals = async () => {
    const nextAttributes = manualDefaults(linkedRecords, attributes);
    const changed = Object.keys(nextAttributes).some((key) => nextAttributes[key] !== attributes[key]);
    if (!changed) {
      toast.message("Non ci sono nuovi dati certi da applicare dai manuali disponibili");
      return;
    }
    setCompleting(true);
    try {
      const { data } = await api.put(`/cards/${id}`, { attributes: nextAttributes });
      setCard(data);
      toast.success("Applicati solo i dati deterministici trovati nei manuali");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Impossibile aggiornare la scheda");
    } finally {
      setCompleting(false);
    }
  };

  return (
    <div className="min-h-screen bg-obsidian">
      <Navbar />
      <main className="character-sheet-page mx-auto max-w-6xl px-4 py-8 sm:px-8">
        <div className="no-print flex flex-wrap items-center justify-between gap-3">
          <button onClick={() => navigate(`/carta/${id}`)} className="flex items-center gap-1.5 font-label text-xs tracking-widest text-muted-foreground transition-colors hover:text-gold">
            <ArrowLeft className="h-4 w-4" /> TORNA AL PERSONAGGIO
          </button>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => navigate(`/carta/${id}/modifica`)} variant="outline" className="rounded-none border-gold-deep/50 bg-transparent font-label text-[11px] tracking-wide text-gold hover:bg-secondary">
              <Pencil className="mr-1.5 h-3.5 w-3.5" /> MODIFICA DATI
            </Button>
            <Button data-testid="print-character-sheet" onClick={() => window.print()} className="rounded-none bg-gold font-label text-[11px] tracking-wide text-obsidian hover:bg-gold-deep">
              <Printer className="mr-1.5 h-3.5 w-3.5" /> STAMPA / SALVA PDF
            </Button>
          </div>
        </div>

        <section className="tf-sheet-a4 mt-7">
        <header className="border border-gold-deep/70 bg-[linear-gradient(135deg,#24160d,#110f0d)] p-6 sm:p-8">
          <p className="font-label text-[10px] tracking-[0.3em] text-gold/70">SCHEDA DEL PERSONAGGIO</p>
          <div className="mt-3 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
            <div>
              <h1 className="font-display text-4xl tf-gold-text sm:text-6xl">{card.name || "Personaggio senza nome"}</h1>
              <p className="mt-2 font-body text-base text-foreground/80">{identity || "Aggiungi razza e classe per completare l’identità."}</p>
              <p className="mt-1 font-body text-sm text-muted-foreground">Background: {attributes.background || "—"} · Allineamento: {attributes.allineamento || "—"}</p>
            </div>
            <div className="grid grid-cols-3 divide-x divide-gold-deep/50 border border-gold-deep/50 bg-obsidian/55 text-center">
              <div className="px-4 py-3"><p className="font-label text-[9px] tracking-widest text-gold/75">LIVELLO</p><p className="mt-1 font-heading text-2xl text-foreground">{level}</p></div>
              <div className="px-4 py-3"><p className="font-label text-[9px] tracking-widest text-gold/75">CA</p><p className="mt-1 font-heading text-2xl text-foreground">{attributes.classe_armatura || "—"}</p></div>
              <div className="px-4 py-3"><p className="font-label text-[9px] tracking-widest text-gold/75">PF</p><p className="mt-1 font-heading text-2xl text-foreground">{attributes.punti_ferita || "—"}</p></div>
            </div>
          </div>
        </header>

        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {ABILITIES.map(([key, short, label]) => (
            <div key={key} className="border border-gold-deep/55 bg-card p-4 text-center">
              <p className="font-label text-[10px] tracking-[0.22em] text-gold">{short}</p>
              <p className="mt-1 font-heading text-3xl text-foreground">{attributes[key] || "—"}</p>
              <p className="mt-1 font-body text-sm text-muted-foreground">{formatMod(attributes[key])} · {label}</p>
            </div>
          ))}
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.1fr_.9fr]">
          <div className="space-y-6">
            <section className="border border-gold-deep/45 bg-card/75 p-5">
              <h2 className="font-label text-xs tracking-[0.18em] text-gold">VALORI DI GIOCO</h2>
              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
                {[
                  ["Bonus competenza", proficiency],
                  ["Dadi vita", attributes.dadi_vita || "—"],
                  ["PF attuali", attributes.pf_attuali || "—"],
                  ["PF temporanei", attributes.pf_temporanei || "—"],
                  ["Velocità", attributes.velocita || "—"],
                  ["CD incantesimi", attributes.cd_incantesimi || "—"],
                ].map(([label, value]) => (
                  <div key={label} className="border border-border/80 bg-obsidian/45 px-3 py-3">
                    <p className="font-label text-[9px] tracking-widest text-gold/70">{label.toUpperCase()}</p>
                    <p className="mt-1 font-body text-base text-foreground">{value}</p>
                  </div>
                ))}
              </div>
            </section>

            <ValueList title="COMPETENZE E TIRI SALVEZZA" values={[...asList(attributes.tiri_salvezza), ...asList(attributes.competenze)]} />
            <ValueList title="ARMI E TRUCCHI DA COMBATTIMENTO" values={asList(attributes.armi_trucchi)} empty="Aggiungi attacchi, armi o trucchi dal personaggio." />
          </div>

          <div className="space-y-6">
            <ValueList title="PRIVILEGI DI CLASSE" values={capabilities} />
            <ValueList title="TRATTI DELLA SPECIE" values={asList(attributes.tratti_razza)} />
            <ValueList title="TALENTI" values={asList(attributes.talenti)} />
            <section className="border border-gold-deep/45 bg-card/75 p-5">
              <h2 className="font-label text-xs tracking-[0.18em] text-gold">ADDESTRAMENTO E COMPETENZE NELL’EQUIPAGGIAMENTO</h2>
              <div className="mt-3 space-y-2 font-body text-sm">
                <p><strong>Armature:</strong> {attributes.competenza_armature || "—"}</p>
                <p><strong>Armi:</strong> {attributes.competenze_armi || "—"}</p>
                <p><strong>Strumenti:</strong> {attributes.strumenti || "—"}</p>
              </div>
            </section>
          </div>
        </div>
        </section>

        <section className="tf-sheet-a4 mt-7">
          <div className="grid gap-6 lg:grid-cols-[1.15fr_.85fr]">
            <div className="space-y-6">
              <section className="border border-gold-deep/45 bg-card/75 p-5">
                <h2 className="font-label text-xs tracking-[0.18em] text-gold">CARATTERISTICA DA INCANTATORE</h2>
                <div className="mt-3 grid grid-cols-3 gap-3">
                  {[
                    ["Caratteristica", attributes.caratteristica_incantatore || "—"],
                    ["Modificatore", attributes.modificatore_incantatore || "—"],
                    ["Bonus attacco", attributes.bonus_attacco_incantesimi || "—"],
                    ["CD tiro salvezza", attributes.cd_incantesimi || "—"],
                  ].map(([label, value]) => (
                    <div key={label} className="border border-border/80 bg-obsidian/45 px-3 py-3">
                      <p className="font-label text-[9px] tracking-widest text-gold/70">{label.toUpperCase()}</p>
                      <p className="mt-1 font-body text-base text-foreground">{value}</p>
                    </div>
                  ))}
                </div>
              </section>
              <section className="border border-gold-deep/45 bg-card/75 p-5">
                <h2 className="font-label text-xs tracking-[0.18em] text-gold">SLOT INCANTESIMI</h2>
                {(attributes.slot_incantesimi || []).filter((slot) => slot && (slot.livello || slot.totale)).length ? (
                  <div className="mt-3 grid grid-cols-3 gap-2">
                    {attributes.slot_incantesimi.filter((slot) => slot && (slot.livello || slot.totale)).map((slot, index) => (
                      <div key={`${slot.livello}-${index}`} className="border border-border/70 bg-obsidian/45 px-3 py-2 font-body text-sm">
                        <span>Livello {slot.livello || index + 1}</span>
                        <span className="float-right text-gold">{Math.max(0, Number(slot.totale || 0) - Number(slot.usati || 0))}/{slot.totale || 0}</span>
                      </div>
                    ))}
                  </div>
                ) : <p className="mt-3 font-body text-sm text-muted-foreground">Nessuno slot inserito.</p>}
              </section>
              <ValueList title="TRUCCHETTI E INCANTESIMI PREPARATI" values={asList(attributes.incantesimi)} empty="Aggiungi gli incantesimi scelti dal personaggio." />
            </div>
            <div className="space-y-6">
              <ValueList title="ASPETTO" values={asList(attributes.aspetto)} empty="Descrivi l’aspetto del personaggio." />
              <ValueList title="STORIA E TRATTI CARATTERIALI" values={[card.description, card.story].filter(Boolean)} empty="Aggiungi note, storia e tratti al personaggio." />
              <section className="border border-gold-deep/45 bg-card/75 p-5">
                <h2 className="font-label text-xs tracking-[0.18em] text-gold">LINGUE</h2>
                <p className="mt-3 font-body text-sm leading-relaxed text-foreground/90">{asList(attributes.linguaggi).join(" · ") || "Nessuna lingua inserita."}</p>
              </section>
              <ValueList title="EQUIPAGGIAMENTO" values={asList(attributes.equipaggiamento)} empty="Aggiungi l’equipaggiamento del personaggio." />
              <section className="border border-gold-deep/45 bg-card/75 p-5">
                <h2 className="font-label text-xs tracking-[0.18em] text-gold">DENARI E SINTONIA</h2>
                <p className="mt-3 font-body text-sm"><strong>Denari:</strong> {attributes.denari || "—"}</p>
                <p className="mt-2 font-body text-sm"><strong>Sintonia:</strong> {asList(attributes.sintonia).join(" · ") || "—"}</p>
              </section>
            </div>
          </div>
        </section>

        <section className="no-print mt-6 border border-sky-700/45 bg-sky-950/15 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-label text-[10px] tracking-[0.2em] text-sky-200">CARTE COLLEGATE DALLA BIBLIOTECA</p>
              <p className="mt-1 font-body text-sm text-muted-foreground">Razza, classe e sottoclasse vengono cercate nella tua biblioteca. Puoi applicare solo i campi certi mancanti oppure aprire un record nel laboratorio carte.</p>
            </div>
            <div className="flex items-center gap-2">
              {loadingLinks && <Loader2 className="h-4 w-4 animate-spin text-sky-200" />}
              <Button size="sm" data-testid="complete-sheet-from-manuals" onClick={completeFromManuals} disabled={loadingLinks || completing || !linkedRecords.length} className="rounded-none bg-sky-700 text-[10px] font-label tracking-wide text-white hover:bg-sky-600">
                {completing ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : <BookOpen className="mr-1 h-3 w-3" />} COMPLETA DAI MANUALI
              </Button>
            </div>
          </div>
          {linkedRecords.length ? (
            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              {linkedRecords.map((record) => (
                <div key={record.id} className="flex items-center justify-between gap-3 border border-sky-900/70 bg-obsidian/45 p-3">
                  <div className="min-w-0">
                    <p className="font-heading text-base text-foreground">{record.name}</p>
                    <p className="mt-0.5 truncate font-body text-[11px] text-muted-foreground">{record.reference_type?.replaceAll("_", " ")}</p>
                  </div>
                  <Button size="sm" onClick={() => navigate(`/crea?referenceId=${encodeURIComponent(record.id)}`)} className="shrink-0 rounded-none bg-sky-700 text-[10px] font-label tracking-wide text-white hover:bg-sky-600">
                    <Sparkles className="mr-1 h-3 w-3" /> CARTA
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-4 font-body text-sm text-muted-foreground">{libraryNotice || "Aggiungi classe o razza al personaggio per trovare i riferimenti. Se un contenuto non è ancora nella biblioteca, la scheda non lo inventa."}</p>
          )}
          {linkedRecords.length > 0 && libraryNotice && (
            <p className="mt-4 border-l-2 border-amber-500/60 pl-3 font-body text-xs leading-relaxed text-amber-100/80">{libraryNotice}</p>
          )}
          {sourceRecords.length > 0 && (
            <p className="mt-4 border-t border-sky-900/60 pt-3 font-body text-[11px] text-sky-100/70">
              Fonti disponibili: {sourceRecords.flatMap((record) => record.source_refs).map((ref) => `${ref.filename} p.${ref.page}`).filter((value, index, array) => array.indexOf(value) === index).join(" · ")}
            </p>
          )}
        </section>

        {(card.description || card.story) && (
          <section className="mt-6 border border-gold-deep/45 bg-card/75 p-5">
            <h2 className="font-label text-xs tracking-[0.18em] text-gold">NOTE DEL PERSONAGGIO</h2>
            {card.description && <p className="mt-3 whitespace-pre-wrap font-body leading-relaxed text-foreground/90">{card.description}</p>}
            {card.story && <p className="mt-3 whitespace-pre-wrap border-t border-border/70 pt-3 font-body text-sm leading-relaxed text-muted-foreground">{card.story}</p>}
          </section>
        )}
      </main>
    </div>
  );
}