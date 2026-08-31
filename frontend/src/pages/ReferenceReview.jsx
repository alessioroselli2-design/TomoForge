import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertTriangle, BookCheck, CheckCircle2, Loader2, RefreshCw, Search, XCircle } from "lucide-react";
import { toast } from "sonner";

import Navbar from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";

const inputCls = "rounded-none border-border bg-input font-body focus-visible:ring-gold";

const typeLabels = {
  spell: "Incantesimo", class: "Classe", subclass: "Sottoclasse", class_feature: "Privilegio",
  ability: "Capacità", feat: "Talento", race: "Razza", subrace: "Sottorazza", monster: "Mostro",
  weapon: "Arma", armor: "Armatura", shield: "Scudo", equipment: "Equipaggiamento", tool: "Strumento",
  magic_item: "Oggetto magico", vehicle: "Veicolo", ammunition: "Munizione", mount: "Cavalcatura",
  trade_good: "Merce", service: "Servizio", other: "Altro",
};

const makeDraft = (record = {}) => ({
  name: record.translation?.name ?? record.name ?? "",
  description: record.translation?.description ?? record.description ?? "",
  full_text: record.translation?.full_text ?? record.full_text ?? "",
  attributes: JSON.stringify(record.translation?.attributes ?? record.attributes ?? {}, null, 2),
  review_notes: record.review_notes ?? "",
});

const pageLabel = (references = []) => references
  .map((reference) => `${reference.filename || "Manuale"} · pagina ${reference.page || "?"}`)
  .join(" · ");

export default function ReferenceReview() {
  const [searchParams] = useSearchParams();
  const types = searchParams.get("types") || "";
  const sourceFilename = searchParams.get("source") || "";
  const [query, setQuery] = useState("");
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);
  const [selected, setSelected] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [saving, setSaving] = useState(null);
  const [draft, setDraft] = useState(makeDraft());

  const loadQueue = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get("/library", {
        params: {
          ...(query.trim() ? { q: query.trim() } : {}),
          ...(types ? { types } : {}),
          ...(sourceFilename ? { source_filename: sourceFilename } : {}),
          review_only: true,
          include_unverified: true,
          limit: 8000,
        },
      });
      const nextRecords = response.data.records || [];
      setRecords(nextRecords);
      setSelectedId((current) => (
        current && nextRecords.some((record) => record.id === current)
          ? current
          : nextRecords[0]?.id || null
      ));
    } catch (error) {
      setRecords([]);
      setSelectedId(null);
      toast.error(error.response?.data?.detail || "Impossibile caricare la coda di revisione");
    } finally {
      setLoading(false);
    }
  }, [query, sourceFilename, types]);

  useEffect(() => {
    const timer = window.setTimeout(loadQueue, query ? 220 : 0);
    return () => window.clearTimeout(timer);
  }, [loadQueue, query]);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      return undefined;
    }
    let active = true;
    setLoadingDetail(true);
    api.get(`/library/${selectedId}/review`)
      .then((response) => {
        if (!active) return;
        setSelected(response.data);
        setDraft(makeDraft(response.data));
      })
      .catch((error) => {
        if (active) toast.error(error.response?.data?.detail || "Impossibile aprire il contenuto");
      })
      .finally(() => { if (active) setLoadingDetail(false); });
    return () => { active = false; };
  }, [selectedId]);

  const queueLabel = useMemo(() => {
    if (loading) return "Caricamento…";
    return `${records.length} ${records.length === 1 ? "record da verificare" : "record da verificare"}`;
  }, [loading, records.length]);

  const submit = async (reviewStatus) => {
    if (!selected?.id) return;
    if (!draft.name.trim()) {
      toast.error("Inserisci il nome corretto del contenuto");
      return;
    }
    if (reviewStatus === "verified" && !draft.full_text.trim()) {
      toast.error("Inserisci il testo completo corretto prima di verificare");
      return;
    }
    let attributes;
    try {
      attributes = JSON.parse(draft.attributes || "{}");
      if (!attributes || Array.isArray(attributes) || typeof attributes !== "object") throw new Error("invalid");
    } catch {
      toast.error("Gli attributi devono essere un oggetto JSON valido");
      return;
    }
    setSaving(reviewStatus);
    try {
      const response = await api.patch(`/library/${selected.id}/review`, {
        review_status: reviewStatus,
        review_notes: draft.review_notes.trim(),
        name: draft.name.trim(),
        description: draft.description.trim(),
        full_text: draft.full_text.trim(),
        attributes,
      });
      if (reviewStatus === "verified") {
        const remaining = records.filter((record) => record.id !== selected.id);
        setRecords(remaining);
        setSelectedId(remaining[0]?.id || null);
        setSelected(null);
        toast.success("Contenuto verificato e ora utilizzabile nelle carte");
      } else {
        setSelected(response.data);
        setDraft(makeDraft(response.data));
        setRecords((current) => current.map((record) => (
          record.id === selected.id ? { ...record, ...response.data } : record
        )));
        toast.success("Correzioni salvate: il record resta da verificare");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Impossibile salvare la revisione");
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="min-h-screen bg-obsidian">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-8">
        <header className="border-b border-gold-deep/35 pb-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="font-label text-[10px] tracking-[0.28em] text-amber-300">BIBLIOTECA PRIVATA</p>
              <h1 className="mt-2 flex items-center gap-3 font-heading text-3xl text-foreground">
                <BookCheck className="h-7 w-7 text-gold" /> Revisione OCR
              </h1>
              <p className="mt-2 max-w-2xl font-body text-sm leading-relaxed text-muted-foreground">
                Correggi le trascrizioni incerte prima che diventino fonti utilizzabili nelle ricerche e nelle carte.
              </p>
            </div>
            <span className="border border-amber-700/50 bg-amber-950/25 px-3 py-2 font-label text-[10px] tracking-widest text-amber-200">
              {queueLabel}
            </span>
          </div>
        </header>

        <div className="mt-6 grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="border border-border bg-card">
            <div className="flex items-center gap-2 border-b border-border p-3">
              <Search className="h-4 w-4 text-gold/70" />
              <Input
                data-testid="review-queue-search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Cerca nella coda…"
                className={inputCls}
              />
              <Button type="button" variant="ghost" size="icon" onClick={loadQueue} aria-label="Aggiorna coda">
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
            {loading ? (
              <p className="flex items-center gap-2 p-4 font-body text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Caricamento…
              </p>
            ) : records.length === 0 ? (
              <div className="p-6 text-center">
                <CheckCircle2 className="mx-auto h-8 w-8 text-emerald-400" />
                <p className="mt-3 font-heading text-lg text-foreground">Coda completata</p>
                <p className="mt-1 font-body text-xs text-muted-foreground">Non ci sono contenuti da verificare con questi filtri.</p>
              </div>
            ) : (
              <ul className="max-h-[70vh] overflow-y-auto divide-y divide-border">
                {records.map((record) => (
                  <li key={record.id}>
                    <button
                      type="button"
                      data-testid={`review-queue-record-${record.id}`}
                      onClick={() => setSelectedId(record.id)}
                      className={`w-full px-4 py-3 text-left transition-colors ${selectedId === record.id ? "bg-amber-950/30" : "hover:bg-secondary"}`}
                    >
                      <span className="block font-heading text-base text-foreground">{record.name}</span>
                      <span className="mt-1 block font-label text-[9px] tracking-widest text-amber-200">DA VERIFICARE · {typeLabels[record.reference_type] || "Contenuto"}</span>
                      <span className="mt-1 block truncate font-body text-[11px] text-muted-foreground">{pageLabel(record.source_refs)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </aside>

          <section className="min-w-0 border border-gold-deep/40 bg-card p-4 sm:p-6">
            {loadingDetail ? (
              <p className="flex items-center gap-2 font-body text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Apertura del contenuto…
              </p>
            ) : !selected ? (
              <p className="font-body text-sm text-muted-foreground">Seleziona un record dalla coda per iniziare la revisione.</p>
            ) : (
              <>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-label text-[10px] tracking-widest text-amber-200">DA VERIFICARE</p>
                    <h2 className="mt-1 font-heading text-2xl text-foreground">{selected.name}</h2>
                    <p className="mt-1 font-body text-xs text-muted-foreground">{pageLabel(selected.manual || selected.source_refs)}</p>
                  </div>
                  <p className="max-w-sm font-body text-xs leading-relaxed text-amber-100/75">
                    <AlertTriangle className="mr-1 inline h-3.5 w-3.5" /> {selected.review_reason}
                  </p>
                </div>

                <div className="mt-5 grid gap-4 xl:grid-cols-2">
                  <article className="border border-amber-700/40 bg-amber-950/15 p-4">
                    <p className="font-label text-[9px] tracking-widest text-amber-200">ESTRATTO ORIGINALE · SOLA LETTURA</p>
                    <h3 className="mt-2 font-heading text-lg text-foreground">{selected.original?.name || "Fonte originale"}</h3>
                    <p className="mt-3 whitespace-pre-wrap font-body text-xs leading-relaxed text-foreground/80">
                      {selected.original?.full_text || "Testo originale non disponibile."}
                    </p>
                  </article>

                  <div className="space-y-3 border border-sky-700/40 bg-sky-950/15 p-4">
                    <p className="font-label text-[9px] tracking-widest text-sky-200">CONTENUTO CORRETTO</p>
                    <div>
                      <Label htmlFor="review-name" className="font-label text-[9px] tracking-widest text-muted-foreground">NOME</Label>
                      <Input id="review-name" data-testid="review-name" value={draft.name} onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))} className={`${inputCls} mt-1`} />
                    </div>
                    <div>
                      <Label htmlFor="review-description" className="font-label text-[9px] tracking-widest text-muted-foreground">DESCRIZIONE BREVE</Label>
                      <Textarea id="review-description" data-testid="review-description" value={draft.description} onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))} className={`${inputCls} mt-1 min-h-[80px]`} />
                    </div>
                    <div>
                      <Label htmlFor="review-full-text" className="font-label text-[9px] tracking-widest text-muted-foreground">TESTO COMPLETO</Label>
                      <Textarea id="review-full-text" data-testid="review-full-text" value={draft.full_text} onChange={(event) => setDraft((current) => ({ ...current, full_text: event.target.value }))} className={`${inputCls} mt-1 min-h-[220px]`} />
                    </div>
                    <div>
                      <Label htmlFor="review-attributes" className="font-label text-[9px] tracking-widest text-muted-foreground">ATTRIBUTI STRUTTURATI (JSON)</Label>
                      <Textarea id="review-attributes" data-testid="review-attributes" value={draft.attributes} onChange={(event) => setDraft((current) => ({ ...current, attributes: event.target.value }))} spellCheck={false} className={`${inputCls} mt-1 min-h-[130px] font-mono text-[11px]`} />
                    </div>
                  </div>
                </div>

                <div className="mt-4">
                  <Label htmlFor="review-notes" className="font-label text-[9px] tracking-widest text-muted-foreground">NOTA DELLA REVISIONE</Label>
                  <Textarea id="review-notes" data-testid="review-notes" maxLength={3000} value={draft.review_notes} onChange={(event) => setDraft((current) => ({ ...current, review_notes: event.target.value }))} placeholder="Annota cosa hai corretto o cosa resta da controllare…" className={`${inputCls} mt-1 min-h-[72px]`} />
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <Button type="button" data-testid="verify-review-record" disabled={saving !== null} onClick={() => submit("verified")} className="rounded-none bg-emerald-700 font-label text-[10px] tracking-widest text-white hover:bg-emerald-600">
                    {saving === "verified" ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />} SALVA E SEGNA COME VERIFICATO
                  </Button>
                  <Button type="button" data-testid="keep-review-record" disabled={saving !== null} onClick={() => submit("needs_review")} variant="outline" className="rounded-none border-crimson/60 bg-transparent font-label text-[10px] tracking-widest text-red-200 hover:bg-crimson/15">
                    {saving === "needs_review" ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />} SALVA E MANTIENI DA VERIFICARE
                  </Button>
                </div>

                {(selected.review_history || []).length > 0 && (
                  <div className="mt-6 border-t border-border pt-4">
                    <p className="font-label text-[9px] tracking-widest text-sky-200">ULTIME DECISIONI</p>
                    <ul className="mt-2 space-y-2">
                      {selected.review_history.slice(0, 5).map((entry) => (
                        <li key={entry.id || `${entry.reviewed_at}-${entry.review_status}`} className="border border-border/70 px-3 py-2 font-body text-xs text-muted-foreground">
                          <span className={entry.review_status === "verified" ? "text-emerald-300" : "text-amber-200"}>
                            {entry.review_status === "verified" ? "Verificato" : "Da verificare"}
                          </span>
                          {entry.review_notes ? ` · ${entry.review_notes}` : ""}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}