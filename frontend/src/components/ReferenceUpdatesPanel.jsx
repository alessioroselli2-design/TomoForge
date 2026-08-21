import { BookOpenCheck, RefreshCw, ShieldCheck, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";

const sourceLabel = (snapshot) => (snapshot?.source_refs || [])
  .map((source) => `${source.filename || "Manuale"} · p. ${source.page || "?"}`)
  .join(" · ") || "Fonte senza pagina indicata";

const snapshotText = (snapshot) => (
  snapshot?.full_text || snapshot?.description || "Nessun testo strutturato disponibile."
);

export function ReferenceUpdatesPanel({ updates = [], refreshingReferenceId, onRefresh }) {
  if (!updates.length) return null;

  const changedCount = updates.filter((update) => update.status === "updated").length;
  return (
    <section data-testid="reference-updates-panel" className="border border-amber-600/60 bg-amber-950/20 p-5">
      <div className="flex flex-wrap items-start gap-3">
        <TriangleAlert className="mt-0.5 h-5 w-5 text-amber-300" />
        <div className="min-w-0 flex-1">
          <p className="font-label text-[10px] tracking-widest text-amber-200">FONTI COLLEGATE DA RIVEDERE</p>
          <h2 className="mt-1 font-heading text-2xl text-foreground">
            {changedCount
              ? `${changedCount} ${changedCount === 1 ? "regola è cambiata" : "regole sono cambiate"}`
              : "Una fonte collegata richiede attenzione"}
          </h2>
          <p className="mt-1 max-w-3xl font-body text-xs leading-relaxed text-muted-foreground">
            Confronta l’istantanea salvata con la fonte corrente. L’aggiornamento sostituisce solo i valori ancora identici
            alla vecchia fonte: tiri, scelte e modifiche manuali restano protetti.
          </p>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {updates.map((update) => {
          const current = update.after;
          const before = update.before;
          const isMissing = update.status === "missing";
          const isUntracked = update.status === "untracked";
          const canRefresh = !isMissing;
          return (
            <details key={update.reference_id} className="border border-amber-800/55 bg-obsidian/30 px-3 py-3">
              <summary className="cursor-pointer list-none">
                <div className="flex flex-wrap items-center justify-between gap-2 pr-1">
                  <span>
                    <strong className="font-heading text-base text-foreground">{current?.name || before?.name || "Riferimento rimosso"}</strong>
                    <small className="mt-0.5 block font-body text-[11px] text-muted-foreground">
                      {isMissing
                        ? "La fonte non è più disponibile nella biblioteca privata."
                        : isUntracked
                          ? "Questa carta non aveva ancora un’istantanea di confronto."
                          : `Modificati: ${(update.changed_fields || []).join(", ")}.`}
                    </small>
                  </span>
                  <span className={`font-label text-[10px] tracking-widest ${isMissing ? "text-crimson" : "text-amber-200"}`}>
                    {isMissing ? "NON DISPONIBILE" : isUntracked ? "DA FISSARE" : "AGGIORNATA"}
                  </span>
                </div>
              </summary>

              {!isMissing && !isUntracked && (
                <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
                  <div className="border border-border/70 bg-card/50 p-3">
                    <p className="font-label text-[10px] tracking-widest text-muted-foreground">ISTANTANEA SALVATA</p>
                    <p className="mt-1 font-body text-[11px] text-gold/80">{sourceLabel(before)}</p>
                    <p className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap font-body text-xs leading-relaxed text-foreground/85">
                      {snapshotText(before)}
                    </p>
                  </div>
                  <div className="border border-sky-700/50 bg-sky-950/15 p-3">
                    <p className="font-label text-[10px] tracking-widest text-sky-200">FONTE CORRENTE</p>
                    <p className="mt-1 font-body text-[11px] text-sky-100/80">{sourceLabel(current)}</p>
                    <p className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap font-body text-xs leading-relaxed text-foreground/85">
                      {snapshotText(current)}
                    </p>
                  </div>
                </div>
              )}

              {isUntracked && (
                <p className="mt-3 border-l-2 border-amber-400/70 pl-3 font-body text-xs leading-relaxed text-muted-foreground">
                  Non esiste una versione precedente da confrontare. Puoi fissare ora la fonte corrente come punto di
                  confronto, senza cambiare i dati della carta.
                </p>
              )}

              <div className="mt-4 flex flex-wrap items-center gap-3">
                {canRefresh && (
                  <Button
                    type="button"
                    data-testid={`refresh-reference-${update.reference_id}`}
                    onClick={() => onRefresh(update.reference_id, isUntracked)}
                    disabled={refreshingReferenceId === update.reference_id}
                    className="rounded-none bg-amber-600 text-white hover:bg-amber-500 font-label text-[10px] tracking-wide"
                  >
                    {refreshingReferenceId === update.reference_id
                      ? <RefreshCw className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                      : isUntracked ? <BookOpenCheck className="mr-1.5 h-3.5 w-3.5" /> : <ShieldCheck className="mr-1.5 h-3.5 w-3.5" />}
                    {isUntracked ? "FISSA L’ISTANTANEA" : "AGGIORNA DATI DERIVATI"}
                  </Button>
                )}
                {!isMissing && !isUntracked && (
                  <span className="font-body text-[11px] text-muted-foreground">Le modifiche manuali non vengono sovrascritte.</span>
                )}
              </div>
            </details>
          );
        })}
      </div>
    </section>
  );
}