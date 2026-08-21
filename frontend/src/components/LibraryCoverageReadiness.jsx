import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, Check, ChevronDown, ChevronUp, CircleDashed, RefreshCw, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

const categoryNames = {
  spell: "Incantesimi", class: "Classi", subclass: "Sottoclassi", class_feature: "Privilegi di classe",
  ability: "Capacità", feat: "Talenti", race: "Razze", subrace: "Sottorazze", monster: "Mostri",
  weapon: "Armi", armor: "Armature", shield: "Scudi", equipment: "Equipaggiamento", tool: "Strumenti",
  magic_item: "Oggetti magici", vehicle: "Veicoli", ammunition: "Munizioni", mount: "Cavalcature",
  trade_good: "Merci", service: "Servizi", other: "Altro",
};

const sum = (category, key) => Number(category?.[key] || 0);
const totalFor = (manual, key) => (manual.categories || []).reduce((total, category) => total + sum(category, key), 0);

function StatePill({ tone, children }) {
  const styles = {
    ready: "border-emerald-700/50 bg-emerald-950/30 text-emerald-300",
    review: "border-amber-700/55 bg-amber-950/25 text-amber-200",
    missing: "border-crimson/60 bg-crimson/15 text-red-300",
    neutral: "border-border bg-obsidian/40 text-muted-foreground",
  };
  return <span className={`inline-flex items-center gap-1 border px-2 py-1 font-label text-[9px] tracking-widest ${styles[tone] || styles.neutral}`}>{children}</span>;
}

export default function LibraryCoverageReadiness({ onOpenReviews }) {
  const [manuals, setManuals] = useState([]);
  const [totals, setTotals] = useState({ valid: 0, to_review: 0, missing: 0 });
  const [status, setStatus] = useState("loading");
  const [expanded, setExpanded] = useState(null);

  const loadCoverage = useCallback(async () => {
    setStatus("loading");
    try {
      const response = await api.get("/library/coverage");
      setManuals(response.data?.manuals || []);
      setTotals(response.data?.totals || { valid: 0, to_review: 0, missing: 0 });
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, []);

  useEffect(() => { loadCoverage(); }, [loadCoverage]);

  const classifiedRecords = useMemo(() => totals.valid + totals.to_review, [totals]);
  if (status === "loading") {
    return (
      <section data-testid="library-coverage-loading" className="border border-gold-deep/40 bg-card p-5">
        <div className="h-3 w-48 animate-pulse bg-secondary" /><div className="mt-4 h-8 w-full animate-pulse bg-secondary" />
        <div className="mt-3 h-16 w-full animate-pulse bg-secondary/70" />
      </section>
    );
  }
  if (status === "error") {
    return (
      <section className="border border-crimson/50 bg-crimson/10 p-5">
        <div className="flex items-start gap-3"><AlertCircle className="h-5 w-5 text-red-300" />
          <div className="flex-1"><p className="font-label text-[10px] tracking-widest text-red-200">REGISTRO DI PRONTEZZA NON DISPONIBILE</p>
            <p className="mt-1 font-body text-xs text-muted-foreground">La biblioteca privata non ha risposto. Nessun contenuto è stato esposto.</p>
          </div>
          <Button type="button" variant="outline" onClick={loadCoverage} className="rounded-none border-crimson/60 font-label text-[10px] tracking-widest"><RefreshCw className="mr-2 h-3.5 w-3.5" />RIPROVA</Button>
        </div>
      </section>
    );
  }
  if (!manuals.length) {
    return (
      <section data-testid="library-coverage-empty" className="border border-gold-deep/40 bg-card p-5">
        <p className="font-label text-[10px] tracking-widest text-gold">PRONTEZZA DELLA BIBLIOTECA</p>
        <p className="mt-2 font-body text-sm text-muted-foreground">Importa un manuale per vedere quali categorie sono affidabili, da verificare o ancora assenti.</p>
      </section>
    );
  }
  return (
    <section data-testid="library-coverage" className="border border-gold-deep/50 bg-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-gold" /><p className="font-label text-[10px] tracking-widest text-gold">REGISTRO DI PRONTEZZA</p></div>
          <h2 className="mt-1 font-heading text-2xl text-foreground">Cosa puoi usare con fiducia</h2>
          <p className="mt-1 max-w-2xl font-body text-xs leading-relaxed text-muted-foreground">Solo conteggi dei record strutturati del tuo account. Il riepilogo non mostra PDF né testo dei manuali.</p>
        </div>
        <button type="button" onClick={loadCoverage} className="flex items-center gap-1.5 font-label text-[10px] tracking-widest text-muted-foreground hover:text-gold"><RefreshCw className="h-3.5 w-3.5" />AGGIORNA</button>
      </div>
      <div className="mt-4 grid grid-cols-3 border-y border-border/70">
        {[["valid", "RECORD PRONTI", "ready"], ["to_review", "RECORD DA RIVEDERE", "review"], ["missing", "CATEGORIE SENZA RECORD", "missing"]].map(([key, label, tone]) => (
          <div key={key} className="border-r border-border/70 px-3 py-3 last:border-r-0"><p className="font-label text-[9px] tracking-widest text-muted-foreground">{label}</p><p className="mt-1 font-heading text-2xl text-foreground">{totals[key]}</p><StatePill tone={tone}>{key === "missing" ? "DA IMPORTARE" : classifiedRecords ? `${Math.round((totals[key] / classifiedRecords) * 100)}%` : "0%"}</StatePill></div>
        ))}
      </div>
      <div className="mt-4 space-y-2">
        {manuals.map((manual) => {
          const ready = totalFor(manual, "valid"); const review = totalFor(manual, "to_review"); const missing = totalFor(manual, "missing");
          const isOpen = expanded === manual.filename;
          return <div key={manual.filename} className="border border-border/80 bg-obsidian/25">
            <button type="button" onClick={() => setExpanded(isOpen ? null : manual.filename)} className="flex w-full items-center gap-3 px-3 py-3 text-left hover:bg-secondary/40">
              <CircleDashed className="h-4 w-4 shrink-0 text-gold/80" /><span className="min-w-0 flex-1"><strong className="block truncate font-heading text-base text-foreground">{manual.title || manual.filename}</strong><small className="font-body text-[11px] text-muted-foreground">{manual.source_language?.toUpperCase() || "—"} · {ready + review} record classificati · {missing} categorie senza record</small></span>
              <span className="hidden gap-1.5 sm:flex"><StatePill tone="ready"><Check className="h-3 w-3" />{ready}</StatePill><StatePill tone="review">{review}</StatePill><StatePill tone="missing">{missing}</StatePill></span>{isOpen ? <ChevronUp className="h-4 w-4 text-gold" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
            </button>
            {isOpen && <div className="border-t border-border/70 px-3 pb-3 pt-2">
              <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                {(manual.categories || []).map((category) => {
                  const cReady = sum(category, "valid"); const cReview = sum(category, "to_review"); const cMissing = sum(category, "missing");
                  const usefulness = cReady ? "UTILIZZABILE" : cReview ? "RICHIEDE REVISIONE" : "NON DISPONIBILE";
                  return <div key={category.reference_type} className="flex items-center gap-2 border border-border/60 px-2.5 py-2"><span className="min-w-0 flex-1 truncate font-body text-xs text-foreground">{categoryNames[category.reference_type] || category.reference_type}</span><span className={`font-label text-[9px] tracking-widest ${cReady ? "text-emerald-300" : cReview ? "text-amber-200" : "text-red-300"}`}>{usefulness}</span><span className="font-body text-[11px] text-muted-foreground">{cReady} pronti · {cReview} da rivedere{cMissing ? " · nessun record" : ""}</span>{cReview > 0 && <button type="button" onClick={() => onOpenReviews?.(category.reference_type, manual.filename)} className="font-label text-[9px] tracking-widest text-gold hover:text-amber-200">REVISIONI</button>}</div>;
                })}
              </div>
              {onOpenReviews && review > 0 && <Button type="button" onClick={() => onOpenReviews((manual.categories || []).filter((c) => c.to_review).map((c) => c.reference_type).join(","), manual.filename)} className="mt-3 rounded-none bg-amber-700 px-3 font-label text-[10px] tracking-widest text-white hover:bg-amber-600">APRI RECORD DA RIVEDERE</Button>}
            </div>}
          </div>;
        })}
      </div>
    </section>
  );
}