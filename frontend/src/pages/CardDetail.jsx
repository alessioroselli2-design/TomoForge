import { useEffect, useState, useRef, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import jsPDF from "jspdf";
import {
  ArrowLeft, Pencil, Trash2, Download, Printer, RotateCw, Moon, Plus, Minus, FileText, Loader2, ImageDown, Link2,
} from "lucide-react";
import { api } from "@/lib/api";
import { typeLabel, attrLabel, DEFAULT_APPEARANCE } from "@/lib/cardTypes";
import Navbar from "@/components/Navbar";
import { CardFront, CardBack } from "@/components/TradingCard";
import { Button } from "@/components/ui/button";
import { ReferenceUpdatesPanel } from "@/components/ReferenceUpdatesPanel";
import { CardHistoryPanel } from "@/components/CardHistoryPanel";
import { addCharacterSheetPdfPage, addSingleCardA4PdfPages, addSingleCardPdfPages, createCardPng } from "@/lib/cardExport";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

const ABILITIES = ["for", "des", "cos", "int", "sag", "car"];
const isScalar = (v) => typeof v === "string" || typeof v === "number";

const StatBlock = ({ card }) => {
  const a = card.attributes || {};
  const abil = ABILITIES.filter((k) => a[k] !== undefined && a[k] !== "");
  const scalarKeys = Object.keys(a).filter((k) => isScalar(a[k]) && a[k] !== "" && !ABILITIES.includes(k));
  const listKeys = Object.keys(a).filter((k) => Array.isArray(a[k]) && a[k].length && typeof a[k][0] === "string");
  const objListKeys = Object.keys(a).filter((k) => Array.isArray(a[k]) && a[k].length && typeof a[k][0] === "object");

  return (
    <div className="border border-gold-deep/50 bg-card p-6">
      <hr className="tf-divider mb-4" aria-hidden="true" />
      {abil.length > 0 && (
        <div className="grid grid-cols-6 gap-2 mb-5">
          {abil.map((k) => (
            <div key={k} className="text-center border border-gold-deep/40 bg-obsidian/50 py-2">
              <div className="font-label text-[10px] tracking-widest text-gold uppercase">{k}</div>
              <div className="font-body text-lg text-foreground">{a[k]}</div>
            </div>
          ))}
        </div>
      )}
      <div className="space-y-1.5">
        {scalarKeys.map((k) => (
          <div key={k} className="flex gap-2 text-sm border-b border-border/50 pb-1.5">
            <span className="font-label text-xs tracking-wide text-gold/80 uppercase min-w-[120px]">{attrLabel(k)}</span>
            <span className="font-body text-foreground/90">{a[k]}</span>
          </div>
        ))}
      </div>
      {listKeys.map((k) => (
        <div key={k} className="mt-4">
          <div className="font-label text-xs tracking-widest text-gold uppercase mb-2">{attrLabel(k)}</div>
          <ul className="list-disc list-inside space-y-1">
            {a[k].filter((x) => String(x).trim()).map((item, i) => (
              <li key={i} className="font-body text-sm text-foreground/90">{item}</li>
            ))}
          </ul>
        </div>
      ))}
      {objListKeys.filter((k) => k !== "slot_incantesimi").map((k) => (
        <div key={k} className="mt-4">
          <hr className="tf-divider-red mb-3" aria-hidden="true" />
          <div className="font-label text-xs tracking-widest text-gold uppercase mb-2">{attrLabel(k)}</div>
          <div className="space-y-2">
            {a[k].map((obj, i) => (
              <div key={i} className="font-body text-sm">
                <span className="font-semibold text-gold/90">{obj.nome || obj.name}. </span>
                <span className="text-foreground/85">{obj.descrizione || obj.description}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

const SpellSlots = ({ card, onUpdate }) => {
  const slots = (card.attributes?.slot_incantesimi || []).filter((s) => s && (s.livello || s.totale));
  if (!slots.length) return null;

  const setUsed = (idx, delta) => {
    const next = slots.map((s, i) => {
      if (i !== idx) return s;
      const total = Number(s.totale) || 0;
      const used = Math.max(0, Math.min(total, (Number(s.usati) || 0) + delta));
      return { ...s, usati: used };
    });
    onUpdate(next);
  };
  const longRest = () => onUpdate(slots.map((s) => ({ ...s, usati: 0 })));

  return (
    <div className="border border-gold-deep/50 bg-card p-6" data-testid="spell-slots">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-heading text-xl text-gold">Slot Incantesimi</h3>
        <Button data-testid="long-rest-btn" onClick={longRest} variant="outline"
          className="rounded-none border-gold-deep/50 bg-transparent text-gold hover:bg-secondary font-label text-[11px] tracking-wide h-8">
          <Moon className="w-3.5 h-3.5 mr-1.5" /> RIPOSO LUNGO
        </Button>
      </div>
      <div className="space-y-3">
        {slots.map((s, i) => {
          const total = Number(s.totale) || 0;
          const used = Number(s.usati) || 0;
          return (
            <div key={i} className="flex items-center justify-between gap-4 border-b border-border/50 pb-3">
              <span className="font-label text-xs tracking-widest text-gold/80 uppercase">Livello {s.livello || i + 1}</span>
              <div className="flex items-center gap-2 flex-1 justify-center">
                {Array.from({ length: total }).map((_, k) => (
                  <span key={k} className={`w-4 h-4 border rotate-45 ${k < total - used ? "bg-gold border-gold" : "bg-transparent border-gold-deep/60"}`} />
                ))}
              </div>
              <div className="flex items-center gap-2">
                <button data-testid={`slot-minus-${i}`} onClick={() => setUsed(i, 1)} disabled={used >= total}
                  className="w-8 h-8 border border-gold-deep/60 text-gold flex items-center justify-center hover:bg-secondary disabled:opacity-30 transition-colors">
                  <Minus className="w-4 h-4" />
                </button>
                <span className="font-body text-sm text-foreground min-w-[48px] text-center">{total - used}/{total}</span>
                <button data-testid={`slot-plus-${i}`} onClick={() => setUsed(i, -1)} disabled={used <= 0}
                  className="w-8 h-8 border border-gold-deep/60 text-gold flex items-center justify-center hover:bg-secondary disabled:opacity-30 transition-colors">
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const sheetValue = (value) => value !== undefined && value !== null && String(value).trim() ? value : "—";
const compactNames = (items = []) => (items || [])
  .map((item) => typeof item === "string" ? item : item?.nome || item?.name)
  .filter(Boolean)
  .join(" · ") || "—";

const CharacterSheetPreview = ({ card }) => {
  const a = card.attributes || {};
  return (
    <section data-testid="character-sheet" className="border-2 border-[#8c6a2e] bg-[#f5edd7] p-5 text-[#34220e] shadow-xl">
      <div className="border border-[#b69347] p-4">
        <p className="text-center font-label text-[10px] tracking-[0.25em] text-[#765925]">TOMEFORGE</p>
        <h2 className="mt-1 text-center font-display text-2xl text-[#34220e]">Scheda del personaggio</h2>
        <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-4">
          <SheetCell label="Nome" value={sheetValue(card.name)} className="sm:col-span-2" />
          <SheetCell label="Livello" value={sheetValue(a.livello)} />
          <SheetCell label="Classe armatura" value={sheetValue(a.classe_armatura)} />
          <SheetCell label="Razza" value={sheetValue(a.razza)} />
          <SheetCell label="Classe" value={sheetValue(a.classe)} />
          <SheetCell label="Sottoclasse" value={sheetValue(a.sottoclasse)} />
          <SheetCell label="Punti ferita" value={sheetValue(a.punti_ferita)} />
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-6">
          {ABILITIES.map((key) => (
            <div key={key} className="border border-[#8c6a2e] bg-[#34220e] py-2 text-center">
              <span className="block font-label text-[9px] tracking-widest text-[#f5d77a]">{key.toUpperCase()}</span>
              <strong className="font-body text-lg text-[#fff8e7]">{sheetValue(a[key])}</strong>
            </div>
          ))}
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <SheetCell label="Privilegi" value={compactNames(a.privilegi?.length ? a.privilegi : a.abilita_sottoclasse)} multiline />
          <SheetCell label="Incantesimi" value={compactNames(a.incantesimi)} multiline />
          <SheetCell label="Equipaggiamento" value={compactNames(a.equipaggiamento)} multiline />
          <SheetCell label="Competenze / note" value={sheetValue(a.competenze || card.description)} multiline />
        </div>
        <div className="mt-4 border-t border-[#b69347] pt-3">
          <p className="font-label text-[9px] tracking-widest text-[#765925]">FONTI NORMATIVE COLLEGATE</p>
          <p className="mt-1 font-body text-xs leading-relaxed text-[#51401f]">
            {(card.source_refs || []).map((reference) => `${reference.filename || "Manuale"} · p. ${reference.page || "?"}`).join("  |  ") || "Nessuna fonte normativa collegata."}
          </p>
        </div>
      </div>
    </section>
  );
};

const SheetCell = ({ label, value, className = "", multiline = false }) => (
  <div className={`border border-[#b69347] bg-[#fff8e7]/60 p-2 ${className}`}>
    <span className="block font-label text-[8px] tracking-widest text-[#765925]">{label.toUpperCase()}</span>
    <span className={`tf-wrap-anywhere mt-1 block font-body text-sm font-semibold text-[#34220e] ${multiline ? "min-h-[42px] leading-snug" : "leading-snug"}`}>{value}</span>
  </div>
);

export default function CardDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [card, setCard] = useState(null);
  const [flipped, setFlipped] = useState(false);
  const [busy, setBusy] = useState(false);
  const [exportFeedback, setExportFeedback] = useState("");
  const [linkedReferences, setLinkedReferences] = useState([]);
  const [creatingLinked, setCreatingLinked] = useState(false);
  const [referenceUpdates, setReferenceUpdates] = useState([]);
  const [refreshingReferenceId, setRefreshingReferenceId] = useState(null);
  const [historyBusy, setHistoryBusy] = useState(false);
  const exportFrontRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const res = await api.get(`/cards/${id}`);
      setCard(res.data);
    } catch (e) {
      toast.error("Carta non trovata");
      navigate("/collezione");
    }
  }, [id, navigate]);
  useEffect(() => { load(); }, [load]);

  const loadReferenceUpdates = useCallback(async () => {
    try {
      const response = await api.get(`/cards/${id}/reference-updates`);
      setReferenceUpdates(response.data.updates || []);
    } catch {
      setReferenceUpdates([]);
    }
  }, [id]);
  useEffect(() => { loadReferenceUpdates(); }, [loadReferenceUpdates]);

  useEffect(() => {
    if (card?.type !== "character" || !card.reference_ids?.length) {
      setLinkedReferences([]);
      return undefined;
    }
    let active = true;
    Promise.all(card.reference_ids.map((referenceId) => api.get(`/library/${referenceId}`)
      .then((response) => response.data)
      .catch(() => null)))
      .then((records) => { if (active) setLinkedReferences(records.filter(Boolean)); });
    return () => { active = false; };
  }, [card?.type, card?.reference_ids]);

  const persistAttrs = async (attributes) => {
    setCard((c) => ({ ...c, attributes }));
    try {
      const response = await api.put(`/cards/${id}`, { attributes, version: card.version });
      setCard(response.data);
    } catch (e) {
      if (e.response?.status === 409) await load();
      toast.error(e.response?.data?.detail || "Salvataggio slot fallito");
    }
  };

  const updateSlots = (slots) => {
    persistAttrs({ ...card.attributes, slot_incantesimi: slots });
  };

  const remove = async () => {
    try {
      await api.delete(`/cards/${id}`);
      toast.success("Carta dissolta");
      navigate("/collezione");
    } catch (e) { toast.error("Eliminazione fallita"); }
  };

  const refreshReference = async (referenceId, isUntracked) => {
    setRefreshingReferenceId(referenceId);
    try {
      const response = await api.post(`/cards/${id}/reference-updates`, { reference_ids: [referenceId], version: card.version });
      setCard(response.data.card);
      await loadReferenceUpdates();
      const protectedCount = (response.data.protected_fields?.[referenceId] || []).length;
      if (isUntracked) {
        toast.success("Istantanea della fonte fissata: i dati della carta non sono cambiati");
      } else if (protectedCount) {
        toast.success(`Fonte aggiornata: ${protectedCount} valori manuali sono rimasti invariati`);
      } else {
        toast.success("Dati derivati aggiornati dalla fonte corrente");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Impossibile aggiornare la fonte collegata");
    } finally {
      setRefreshingReferenceId(null);
    }
  };

  const restoreHistory = async (action) => {
    setHistoryBusy(true);
    try {
      const response = await api.post(`/cards/${id}/history/${action}`, { version: card.version });
      setCard(response.data.card);
      await loadReferenceUpdates();
      toast.success(action === "undo" ? "Ultima modifica annullata" : "Modifica ripristinata");
    } catch (error) {
      if (error.response?.status === 409) await load();
      toast.error(error.response?.data?.detail || "Impossibile aggiornare la cronologia");
    } finally {
      setHistoryBusy(false);
    }
  };

  const shareImage = async () => {
    if (!exportFrontRef.current) return;
    setBusy(true);
    try {
      const canvas = await createCardPng(exportFrontRef.current, card);
      const link = document.createElement("a");
      link.download = `${card.name || "carta"}.png`;
      link.href = canvas.toDataURL("image/png");
      link.click();
      setExportFeedback("PNG scaricato: pronto da condividere.");
      toast.success("Immagine esportata");
    } catch (e) { toast.error("Esportazione fallita"); }
    finally { setBusy(false); }
  };

  const exportPDF = async () => {
    if (!exportFrontRef.current) return;
    setBusy(true);
    try {
      const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: [63.5, 88.9] });
      await addSingleCardPdfPages(pdf, exportFrontRef.current, card);
      pdf.save(`${card.name || "carta"}-fronte-retro.pdf`);
      setExportFeedback("PDF fronte/retro generato.");
      toast.success("PDF generato");
    } catch (e) { toast.error("Generazione PDF fallita"); }
    finally { setBusy(false); }
  };

  const exportSheet = async () => {
    if (!exportFrontRef.current) return;
    setBusy(true);
    try {
      const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
      await addSingleCardA4PdfPages(pdf, exportFrontRef.current, card);
      pdf.save(`carta-${card.name || "personaggio"}-a4-fronte-retro.pdf`);
      setExportFeedback("Foglio A4 fronte/retro generato.");
      toast.success("Carta A4 generata");
    } catch (e) { toast.error("Generazione carta A4 fallita"); }
    finally { setBusy(false); }
  };

  const exportCharacterSheet = async () => {
    setBusy(true);
    try {
      const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
      await addCharacterSheetPdfPage(pdf, card);
      pdf.save(`scheda-${card.name || "personaggio"}.pdf`);
      setExportFeedback("Scheda completa A4 generata.");
      toast.success("Scheda PDF generata");
    } catch (e) { toast.error("Generazione della scheda fallita"); }
    finally { setBusy(false); }
  };

  const printCharacterSheet = async () => {
    // Open the print target immediately to avoid browser popup blocking while
    // the fixed A4 canvas is being rendered.
    const printWindow = window.open("", "_blank");
    setBusy(true);
    try {
      const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
      await addCharacterSheetPdfPage(pdf, card);
      const url = URL.createObjectURL(pdf.output("blob"));
      if (printWindow) {
        printWindow.location.href = url;
        window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
      } else {
        pdf.save(`scheda-${card.name || "personaggio"}.pdf`);
        toast.message("Il browser ha bloccato la finestra: usa il PDF scaricato per stampare.");
      }
    } catch (e) {
      printWindow?.close();
      toast.error("Preparazione della stampa fallita");
    } finally { setBusy(false); }
  };

  const createLinkedCards = async (referenceIds) => {
    if (!referenceIds.length) return;
    setCreatingLinked(true);
    try {
      const response = await api.post(`/cards/${id}/linked`, { reference_ids: referenceIds });
      const count = response.data?.length || 0;
      toast.success(`${count} ${count === 1 ? "carta collegata creata" : "carte collegate create"}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Impossibile creare le carte collegate");
    } finally {
      setCreatingLinked(false);
    }
  };

  if (!card) {
    return (
      <div className="min-h-screen bg-obsidian">
        <Navbar />
        <div className="flex items-center justify-center py-32">
          <Loader2 className="w-6 h-6 text-gold animate-spin" />
        </div>
      </div>
    );
  }

  const detailed = card.type === "monster" || card.type === "character";
  const appearance = { ...DEFAULT_APPEARANCE, ...(card.appearance || {}) };
  const textPanelStyle = {
    "--tf-detail-panel-color": appearance.text_panel_color,
    "--tf-detail-text-color": appearance.text_color,
  };

  return (
    <div className="min-h-screen bg-obsidian">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-8 py-8">
        <button data-testid="back-btn" onClick={() => navigate("/collezione")} className="flex items-center gap-1.5 text-muted-foreground hover:text-gold font-label text-xs tracking-widest mb-6 transition-colors">
          <ArrowLeft className="w-4 h-4" /> COLLEZIONE
        </button>

        <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-10">
          {/* Card + actions */}
            <div className="lg:sticky lg:top-24 h-fit">
              <div className="mx-auto w-full max-w-[320px]" style={{ perspective: "1600px" }}>
              <motion.div
                className="relative preserve-3d"
                  style={{ width: "100%", aspectRatio: "2.5/3.5", transformStyle: "preserve-3d" }}
                animate={{ rotateY: flipped ? 180 : 0 }}
                transition={{ duration: 0.7, ease: "easeInOut" }}
              >
                <div className="absolute inset-0 backface-hidden">
                  <CardFront card={card} />
                </div>
                <div className="absolute inset-0 backface-hidden rotate-y-180">
                  <CardBack card={card} />
                </div>
              </motion.div>
            </div>

            <div className="flex justify-center mt-5">
              <button data-testid="flip-btn" onClick={() => setFlipped((f) => !f)}
                className="flex items-center gap-2 font-label text-[11px] tracking-widest text-gold hover:text-gold-deep border border-gold-deep/50 px-5 py-2.5 transition-colors">
                <RotateCw className="w-3.5 h-3.5" /> {flipped ? "MOSTRA FRONTE" : "MOSTRA RETRO"}
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2 mt-5">
              <Button data-testid="edit-btn" onClick={() => navigate(`/carta/${id}/modifica`)} variant="outline"
                className="rounded-none border-gold-deep/50 bg-transparent text-foreground hover:bg-secondary hover:text-gold font-label text-[11px] tracking-wide transition-colors">
                <Pencil className="w-3.5 h-3.5 mr-1.5" /> MODIFICA
              </Button>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button data-testid="delete-btn" variant="outline"
                    className="rounded-none border-crimson/50 bg-transparent text-crimson hover:bg-crimson/10 font-label text-[11px] tracking-wide transition-colors">
                    <Trash2 className="w-3.5 h-3.5 mr-1.5" /> ELIMINA
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent className="bg-card border-gold-deep/40 rounded-none">
                  <AlertDialogHeader>
                    <AlertDialogTitle className="font-heading text-2xl text-foreground">Dissolvere la carta?</AlertDialogTitle>
                    <AlertDialogDescription className="font-body text-muted-foreground">
                      Questa azione è irreversibile. "{card.name}" sarà cancellata dal tuo tomo.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel className="rounded-none font-label text-xs tracking-wide border-border bg-transparent">ANNULLA</AlertDialogCancel>
                    <AlertDialogAction data-testid="confirm-delete" onClick={remove} className="rounded-none font-label text-xs tracking-wide bg-crimson text-foreground hover:bg-crimson/80">ELIMINA</AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>

            </div>
              {card.type === "character" && (
                <Button data-testid="character-sheet-btn" onClick={() => navigate(`/carta/${id}/scheda`)}
                  className="mt-2 w-full rounded-none bg-sky-700 text-white hover:bg-sky-600 font-label text-[11px] tracking-wide transition-colors">
                  <FileText className="w-3.5 h-3.5 mr-1.5" /> APRI SCHEDA PERSONAGGIO
                </Button>
              )}
            <div className="mt-4 border border-gold-deep/40 bg-card/50 p-3">
              <p className="font-label text-[10px] tracking-[0.18em] text-gold">ESPORTA O STAMPA</p>
              <div className="mt-3 grid grid-cols-1 gap-2">
                <Button data-testid="share-btn" onClick={shareImage} disabled={busy} variant="outline"
                  className="justify-start rounded-none border-border bg-transparent text-foreground hover:bg-secondary font-label text-[11px] tracking-wide transition-colors">
                  <ImageDown className="w-3.5 h-3.5 mr-2 text-gold" /> SCARICA PNG
                </Button>
                <Button data-testid="pdf-btn" onClick={exportPDF} disabled={busy} variant="outline"
                  className="justify-start rounded-none border-border bg-transparent text-foreground hover:bg-secondary font-label text-[11px] tracking-wide transition-colors">
                  <Download className="w-3.5 h-3.5 mr-2 text-gold" /> PDF FRONTE / RETRO
                </Button>
                <Button data-testid="sheet-btn" onClick={exportSheet} disabled={busy}
                  className="justify-start rounded-none bg-gold text-obsidian hover:bg-gold-deep font-label text-[11px] tracking-wide transition-colors">
                  {busy ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <FileText className="w-3.5 h-3.5 mr-2" />} FOGLIO A4 FRONTE / RETRO
                </Button>
                {card.type === "character" && (
                  <>
                    <Button data-testid="character-sheet-pdf-btn" onClick={exportCharacterSheet} disabled={busy} variant="outline"
                      className="justify-start rounded-none border-[#b69347] bg-[#f5edd7] text-[#34220e] hover:bg-[#eaddba] font-label text-[11px] tracking-wide transition-colors">
                      <FileText className="w-3.5 h-3.5 mr-2 text-[#765925]" /> SCHEDA COMPLETA A4
                    </Button>
                    <Button data-testid="character-sheet-print-btn" onClick={printCharacterSheet} disabled={busy} variant="outline"
                      className="justify-start rounded-none border-gold-deep/50 bg-transparent text-gold hover:bg-secondary font-label text-[11px] tracking-wide transition-colors">
                      <Printer className="w-3.5 h-3.5 mr-2" /> STAMPA SCHEDA A4
                    </Button>
                  </>
                )}
              </div>
              <p className="mt-3 font-body text-[11px] leading-relaxed text-muted-foreground">
                Il foglio A4 mantiene la dimensione Standard e il retro allineato per la stampa fronte/retro.
              </p>
              <p aria-live="polite" className="mt-2 min-h-4 font-body text-[11px] text-gold/90">
                {busy ? "Preparazione dell’export in corso…" : exportFeedback}
              </p>
            </div>
          </div>

          {/* Info */}
          <div className="space-y-6">
            <div>
              <p className="font-label text-xs tracking-[0.3em] text-gold/70 mb-2">{typeLabel(card.type, card.custom_type).toUpperCase()}</p>
              <h1 className="font-display text-4xl sm:text-5xl tf-gold-text">{card.name}</h1>
            </div>
            {(card.description || card.story) && (
              <div className="tf-detail-text-panel" style={textPanelStyle}>
                {card.description && (
                  <p className="font-body text-lg italic leading-relaxed">{card.description}</p>
                )}
                {card.story && (
                  <div className={card.description ? "mt-4 border-t border-gold-deep/40 pt-4" : ""}>
                    <p className="font-label text-[10px] tracking-widest text-gold/80 mb-1">STORIA</p>
                    <p className="font-body leading-relaxed">{card.story}</p>
                  </div>
                )}
              </div>
            )}

            <ReferenceUpdatesPanel
              updates={referenceUpdates}
              refreshingReferenceId={refreshingReferenceId}
              onRefresh={refreshReference}
            />
            <CardHistoryPanel
              history={card.change_history || []}
              busy={historyBusy}
              onUndo={() => restoreHistory("undo")}
              onRedo={() => restoreHistory("redo")}
            />

            {card.type === "character" && (
              <>
                <CharacterSheetPreview card={card} />
                <section data-testid="linked-rule-cards" className="border border-sky-700/50 bg-sky-950/15 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="flex items-center gap-1.5 font-label text-[10px] tracking-widest text-sky-200"><Link2 className="h-3.5 w-3.5" /> CARTE DAI RIFERIMENTI</p>
                      <h2 className="mt-1 font-heading text-2xl text-foreground">Carte pronte dal tuo personaggio</h2>
                      <p className="mt-1 max-w-2xl font-body text-xs leading-relaxed text-muted-foreground">
                        Ogni carta usa lo stesso record normativo e le stesse fonti della scheda. Nessun contenuto viene inventato o generato con l’AI.
                      </p>
                    </div>
                    {linkedReferences.length > 1 && (
                      <Button data-testid="create-all-linked-cards" onClick={() => createLinkedCards(linkedReferences.map((record) => record.id))} disabled={creatingLinked}
                        className="rounded-none bg-sky-700 text-white hover:bg-sky-600 font-label text-[10px] tracking-wide">
                        {creatingLinked ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <Link2 className="mr-1.5 h-3.5 w-3.5" />} CREA TUTTE
                      </Button>
                    )}
                  </div>
                  {linkedReferences.length ? (
                    <div className="mt-4 divide-y divide-sky-900/60 border border-sky-900/60">
                      {linkedReferences.map((record) => (
                        <div key={record.id} className="flex items-center justify-between gap-3 px-3 py-3">
                          <span className="min-w-0">
                            <strong className="block font-heading text-base text-foreground">{record.name}</strong>
                            <small className="block font-body text-[11px] text-muted-foreground">
                              {typeLabel(record.reference_type === "class_feature" ? "feature" : record.reference_type)} · {(record.source_refs || []).map((reference) => `${reference.filename} p.${reference.page}`).join(", ")}
                            </small>
                          </span>
                          <Button data-testid={`create-linked-card-${record.id}`} onClick={() => createLinkedCards([record.id])} disabled={creatingLinked} variant="outline"
                            className="shrink-0 rounded-none border-sky-700/60 bg-transparent text-sky-200 hover:bg-sky-950 font-label text-[10px] tracking-wide">
                            CREA CARTA
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-4 font-body text-sm text-muted-foreground">Apri “Modifica” e collega i record dalla base normativa per creare razza, classe, sottoclasse, privilegi, incantesimi ed equipaggiamento.</p>
                  )}
                </section>
                <SpellSlots card={card} onUpdate={updateSlots} />
              </>
            )}

            {(detailed || Object.keys(card.attributes || {}).length > 0) && <StatBlock card={card} />}
          </div>
        </div>
      </main>

      {/* Off-screen clean front render used only to load artwork and QR export assets. */}
      <div style={{ position: "fixed", left: -99999, top: 0 }} aria-hidden="true">
        <div ref={exportFrontRef} style={{ width: 340, height: 476 }}>
          <CardFront card={card} exportMode />
        </div>
      </div>

    </div>
  );
}
