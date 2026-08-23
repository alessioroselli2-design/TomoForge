import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, AlertTriangle, Check, ChevronDown, ChevronUp, CircleDashed, Loader2, RefreshCw, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

const categoryNames = {
  spell: "Incantesimi", class: "Classi", subclass: "Sottoclassi", class_feature: "Privilegi di classe",
  ability: "Capacità", feat: "Talenti", race: "Razze", subrace: "Sottorazze", monster: "Mostri",
  weapon: "Armi", armor: "Armature", shield: "Scudi", equipment: "Equipaggiamento", tool: "Strumenti",
  magic_item: "Oggetti magici", vehicle: "Veicoli", ammunition: "Munizioni", mount: "Cavalcature",
  trade_good: "Merci", service: "Servizi", other: "Altro",
};

const CATEGORY_PREVIEW_LIMIT = 5;

const sum = (category, key) => Number(category?.[key] || 0);
const totalFor = (manual, key) => (manual.categories || []).reduce((total, category) => total + sum(category, key), 0);
const catCacheKey = (filename, type) => `${filename}\x00${type}`;

function StatePill({ tone, children }) {
  const styles = {
    ready: "border-emerald-700/50 bg-emerald-950/30 text-emerald-300",
    review: "border-amber-700/55 bg-amber-950/25 text-amber-200",
    missing: "border-crimson/60 bg-crimson/15 text-red-300",
    neutral: "border-border bg-obsidian/40 text-muted-foreground",
  };
  return <span className={`inline-flex items-center gap-1 border px-2 py-1 font-label text-[9px] tracking-widest ${styles[tone] || styles.neutral}`}>{children}</span>;
}

export default function LibraryCoverageReadiness({ onOpenReviews, onTotalsChange, refreshKey = 0 }) {
  const [manuals, setManuals] = useState([]);
  const [totals, setTotals] = useState({ valid: 0, to_review: 0, missing: 0, translation_pending: 0 });
  const [status, setStatus] = useState("loading");
  const [expanded, setExpanded] = useState(null);

  // Category-level record list: null | { filename, type }
  const [expandedCategory, setExpandedCategory] = useState(null);
  // "filename\0type" -> { loading: bool, records: [], error: bool }
  const [categoryRecords, setCategoryRecords] = useState({});
  // Tracks which keys have already been fetched so we never double-fetch
  const fetchedCategoryKeys = useRef(new Set());

  const loadCoverage = useCallback(async () => {
    setStatus("loading");
    // Reset category cache whenever coverage is reloaded so stale records
    // don't linger after the user clicks "AGGIORNA".
    setExpandedCategory(null);
    setCategoryRecords({});
    fetchedCategoryKeys.current = new Set();
    try {
      const response = await api.get("/library/coverage");
      const newTotals = response.data?.totals || { valid: 0, to_review: 0, missing: 0, translation_pending: 0 };
      setManuals(response.data?.manuals || []);
      setTotals(newTotals);
      onTotalsChange?.(newTotals);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, [onTotalsChange]);

  useEffect(() => { loadCoverage(); }, [loadCoverage, refreshKey]);

  const toggleCategory = useCallback(async (filename, type) => {
    const isOpen = expandedCategory?.filename === filename && expandedCategory?.type === type;
    setExpandedCategory(isOpen ? null : { filename, type });

    if (isOpen) return;

    const key = catCacheKey(filename, type);
    // Guard: do not re-fetch if we already started a request for this key
    if (fetchedCategoryKeys.current.has(key)) return;
    fetchedCategoryKeys.current.add(key);

    setCategoryRecords(prev => ({ ...prev, [key]: { loading: true, records: [], error: false } }));
    try {
      const resp = await api.get("/library", {
        params: { types: type, source_filename: filename, review_only: true, include_unverified: true },
      });
      setCategoryRecords(prev => ({
        ...prev,
        [key]: { loading: false, records: resp.data?.records || [], error: false },
      }));
    } catch {
      // Allow re-try on error by removing the key from the guard set
      fetchedCategoryKeys.current.delete(key);
      setCategoryRecords(prev => ({
        ...prev,
        [key]: { loading: false, records: [], error: true },
      }));
    }
  }, [expandedCategory]);

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
        <p className="mt-2 font-body text-sm text-muted-foreground">I tuoi manuali vengono precaricati automaticamente. Una volta completato il primo ciclo vedrai qui quali categorie sono pronte, da verificare o ancora in attesa.</p>
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

      {/* Translation pending strip */}
      {totals.translation_pending > 0 && (
        <div
          data-testid="coverage-translation-pending-strip"
          className="mt-3 flex items-start gap-2 border border-amber-700/55 bg-amber-950/20 px-3 py-2"
        >
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-300" />
          <p className="flex-1 font-body text-[11px] leading-relaxed text-amber-200">
            <strong className="font-label text-[9px] tracking-widest">{totals.translation_pending} TRADUZION{totals.translation_pending === 1 ? "E" : "I"} IN SOSPESO</strong>
            {" — "}
            {totals.translation_pending === 1
              ? "Un record non è stato tradotto automaticamente."
              : `${totals.translation_pending} record non sono stati tradotti automaticamente.`}
            {" "}Verificali manualmente per renderli disponibili.{" "}
            <Link to="/crea#editor-library-import" className="font-label text-[9px] tracking-widest text-amber-300 underline-offset-2 hover:text-amber-100">
              VAI ALL'IMPORTAZIONE →
            </Link>
          </p>
        </div>
      )}

      <div className="mt-4 space-y-2">
        {manuals.map((manual) => {
          const ready = totalFor(manual, "valid");
          const review = totalFor(manual, "to_review");
          const missing = totalFor(manual, "missing");
          const isOpen = expanded === manual.filename;
          return (
            <div key={manual.filename} className="border border-border/80 bg-obsidian/25">
              <button
                type="button"
                onClick={() => setExpanded(isOpen ? null : manual.filename)}
                className="flex w-full items-center gap-3 px-3 py-3 text-left hover:bg-secondary/40"
              >
                <CircleDashed className="h-4 w-4 shrink-0 text-gold/80" />
                <span className="min-w-0 flex-1">
                  <strong className="block truncate font-heading text-base text-foreground">{manual.title || "Manuale importato"}</strong>
                  <small className="font-body text-[11px] text-muted-foreground">
                    {manual.source_language?.toUpperCase() || "—"} · {ready + review} record classificati · {missing} categorie senza record
                  </small>
                </span>
                <span className="hidden gap-1.5 sm:flex">
                  <StatePill tone="ready"><Check className="h-3 w-3" />{ready}</StatePill>
                  <StatePill tone="review">{review}</StatePill>
                  <StatePill tone="missing">{missing}</StatePill>
                </span>
                {isOpen ? <ChevronUp className="h-4 w-4 text-gold" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
              </button>

              {isOpen && (
                <div className="border-t border-border/70 px-3 pb-3 pt-2">
                  <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                    {(manual.categories || []).map((category) => {
                      const cReady = sum(category, "valid");
                      const cReview = sum(category, "to_review");
                      const cMissing = sum(category, "missing");
                      const usefulness = cReady ? "UTILIZZABILE" : cReview ? "RICHIEDE REVISIONE" : "NON DISPONIBILE";
                      const isCatOpen = expandedCategory?.filename === manual.filename && expandedCategory?.type === category.reference_type;
                      const catData = categoryRecords[catCacheKey(manual.filename, category.reference_type)];
                      return (
                        <div
                          key={category.reference_type}
                          className="flex flex-col gap-1 border border-border/60 px-2.5 py-2"
                        >
                          {/* Category header row */}
                          <div className="flex items-center gap-2">
                            <span className="min-w-0 flex-1 truncate font-body text-xs text-foreground">
                              {categoryNames[category.reference_type] || category.reference_type}
                            </span>
                            <span className={`font-label text-[9px] tracking-widest ${cReady ? "text-emerald-300" : cReview ? "text-amber-200" : "text-red-300"}`}>
                              {usefulness}
                            </span>
                            <span className="font-body text-[11px] text-muted-foreground">
                              {cReady} pronti · {cReview} da rivedere{cMissing ? " · nessun record" : ""}
                            </span>
                            {cReview > 0 && (
                              <button
                                type="button"
                                data-testid={`expand-category-${manual.filename}-${category.reference_type}`}
                                onClick={() => toggleCategory(manual.filename, category.reference_type)}
                                className="font-label text-[9px] tracking-widest text-gold hover:text-amber-200"
                                aria-expanded={isCatOpen}
                              >
                                {isCatOpen
                                  ? <ChevronUp className="inline h-3 w-3" />
                                  : <ChevronDown className="inline h-3 w-3" />}
                                {" "}REVISIONI
                              </button>
                            )}
                          </div>

                          {/* Inline record list for "RICHIEDE REVISIONE" categories */}
                          {cReview > 0 && isCatOpen && (
                            <div
                              data-testid={`category-records-list-${manual.filename}-${category.reference_type}`}
                              className="mt-1 border-t border-border/50 pt-1.5"
                            >
                              {catData?.loading && (
                                <p className="flex items-center gap-1.5 font-body text-[11px] text-muted-foreground">
                                  <Loader2 className="h-3 w-3 animate-spin" />Caricamento record…
                                </p>
                              )}
                              {catData?.error && (
                                <p className="font-body text-[11px] text-red-300">Impossibile caricare i record.</p>
                              )}
                              {catData && !catData.loading && !catData.error && catData.records.length === 0 && (
                                <p className="font-body text-[11px] text-muted-foreground">Nessun record da verificare trovato.</p>
                              )}
                              {catData && !catData.loading && !catData.error && catData.records.length > 0 && (
                                <ul className="space-y-0.5">
                                  {catData.records.slice(0, CATEGORY_PREVIEW_LIMIT).map((record) => (
                                    <li
                                      key={record.id}
                                      data-testid={`category-record-item-${record.id}`}
                                      className="flex items-center justify-between gap-2"
                                    >
                                      <span className="min-w-0 flex-1 truncate font-body text-[11px] text-foreground">
                                        {record.name}
                                      </span>
                                      <button
                                        type="button"
                                        onClick={() => onOpenReviews?.(category.reference_type, manual.filename)}
                                        className="shrink-0 font-label text-[9px] tracking-widest text-gold hover:text-amber-200"
                                      >
                                        Rivedi →
                                      </button>
                                    </li>
                                  ))}
                                  {catData.records.length > CATEGORY_PREVIEW_LIMIT && (
                                    <li>
                                      <button
                                        type="button"
                                        data-testid={`category-records-overflow-${manual.filename}-${category.reference_type}`}
                                        onClick={() => onOpenReviews?.(category.reference_type, manual.filename)}
                                        className="font-body text-[11px] text-muted-foreground hover:text-gold"
                                      >
                                        e altri {catData.records.length - CATEGORY_PREVIEW_LIMIT} →
                                      </button>
                                    </li>
                                  )}
                                </ul>
                              )}
                            </div>
                          )}

                          {/* For empty categories, suggest where to import records from */}
                          {cMissing > 0 && !cReady && !cReview && (
                            <p className="font-body text-[10px] text-muted-foreground">
                              Nessun record importato da questo manuale.{" "}
                              <Link to="/crea#editor-library-import" className="text-gold/70 hover:text-gold">
                                Avvia importazione →
                              </Link>
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {onOpenReviews && review > 0 && (
                    <Button
                      type="button"
                      onClick={() => onOpenReviews(
                        (manual.categories || []).filter((c) => c.to_review).map((c) => c.reference_type).join(","),
                        manual.filename,
                      )}
                      className="mt-3 rounded-none bg-amber-700 px-3 font-label text-[10px] tracking-widest text-white hover:bg-amber-600"
                    >
                      APRI RECORD DA RIVEDERE
                    </Button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
