import { History, Redo2, RotateCcw, ShieldCheck, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";

const fieldLabel = (field) => ({
  attributes: "dati della scheda",
  reference_snapshots: "istantanea delle fonti",
  reference_ids: "riferimenti collegati",
  source_refs: "fonti collegate",
  artwork_path: "illustrazione",
  custom_type: "tipo carta",
}[field] || field.replaceAll("_", " "));

const eventLabel = (entry) => {
  if (entry.action === "reference_update") return "Aggiornamento delle regole";
  if (entry.action === "manual_completion") return "Completamento dai manuali";
  return "Modifica della scheda";
};

export function CardHistoryPanel({ history = [], onUndo, onRedo, busy = false }) {
  const canUndo = history.some((entry) => !entry.undone);
  const canRedo = history.some((entry) => entry.undone);
  if (!history.length) return null;

  return (
    <section data-testid="card-change-history" className="border border-emerald-800/55 bg-emerald-950/15 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="flex items-center gap-1.5 font-label text-[10px] tracking-widest text-emerald-200">
            <History className="h-3.5 w-3.5" /> CRONOLOGIA DELLA SCHEDA
          </p>
          <h2 className="mt-1 font-heading text-2xl text-foreground">Modifiche protette</h2>
          <p className="mt-1 max-w-2xl font-body text-xs leading-relaxed text-muted-foreground">
            Le modifiche personali e quelle tratte dai manuali restano separate. Annulla o ripristina l’ultima variazione salvata.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            data-testid="undo-card-change"
            onClick={onUndo}
            disabled={!canUndo || busy}
            variant="outline"
            className="rounded-none border-emerald-700/60 bg-transparent font-label text-[10px] tracking-wide text-emerald-100 hover:bg-emerald-950"
          >
            <RotateCcw className="mr-1.5 h-3.5 w-3.5" /> ANNULLA
          </Button>
          <Button
            type="button"
            data-testid="redo-card-change"
            onClick={onRedo}
            disabled={!canRedo || busy}
            variant="outline"
            className="rounded-none border-emerald-700/60 bg-transparent font-label text-[10px] tracking-wide text-emerald-100 hover:bg-emerald-950"
          >
            <Redo2 className="mr-1.5 h-3.5 w-3.5" /> RIPRISTINA
          </Button>
        </div>
      </div>

      <ol className="mt-4 space-y-2">
        {[...history].reverse().slice(0, 6).map((entry) => {
          const isManual = entry.source === "manual";
          return (
            <li key={entry.id} className={`flex gap-3 border px-3 py-2 ${entry.undone ? "border-border/60 bg-obsidian/25 opacity-65" : "border-emerald-900/55 bg-obsidian/35"}`}>
              {isManual ? <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-sky-300" /> : <UserRound className="mt-0.5 h-4 w-4 shrink-0 text-gold" />}
              <div className="min-w-0">
                <p className="font-body text-xs text-foreground">
                  <strong>{eventLabel(entry)}</strong>
                  <span className={`ml-2 font-label text-[9px] tracking-widest ${isManual ? "text-sky-200" : "text-gold/85"}`}>
                    {isManual ? "MANUALE" : "UTENTE"}
                  </span>
                  {entry.undone && <span className="ml-2 font-label text-[9px] tracking-widest text-muted-foreground">ANNULLATA</span>}
                </p>
                <p className="mt-0.5 font-body text-[11px] text-muted-foreground">
                  {(entry.changed_fields || []).map(fieldLabel).join(" · ") || "Istantanea aggiornata"}
                </p>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}