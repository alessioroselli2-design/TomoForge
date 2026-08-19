import React, { useEffect, useState, useRef, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import jsPDF from "jspdf";
import {
  ArrowLeft, Pencil, Trash2, Download, Printer, RotateCw, Moon, Plus, Minus, FileText, Loader2,
} from "lucide-react";
import { api, artworkUrl } from "@/lib/api";
import { typeLabel, attrLabel } from "@/lib/cardTypes";
import Navbar from "@/components/Navbar";
import { CardFront, CardBack } from "@/components/TradingCard";
import { Button } from "@/components/ui/button";
import { addSingleCardPdfPages, captureCard, createCardPng } from "@/lib/cardExport";
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

export default function CardDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [card, setCard] = useState(null);
  const [flipped, setFlipped] = useState(false);
  const [busy, setBusy] = useState(false);
  const exportFrontRef = useRef(null);
  const sheetRef = useRef(null);

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

  const persistAttrs = async (attributes) => {
    setCard((c) => ({ ...c, attributes }));
    try { await api.put(`/cards/${id}`, { attributes }); }
    catch (e) { toast.error("Salvataggio slot fallito"); }
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

  const shareImage = async () => {
    if (!exportFrontRef.current) return;
    setBusy(true);
    try {
      const canvas = await createCardPng(exportFrontRef.current, card);
      const link = document.createElement("a");
      link.download = `${card.name || "carta"}.png`;
      link.href = canvas.toDataURL("image/png");
      link.click();
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
      toast.success("PDF generato");
    } catch (e) { toast.error("Generazione PDF fallita"); }
    finally { setBusy(false); }
  };

  const exportSheet = async () => {
    if (!sheetRef.current) return;
    setBusy(true);
    try {
      const canvas = await captureCard(sheetRef.current, "#fefdf9");
      const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
      const w = 210, h = (canvas.height * w) / canvas.width;
      pdf.addImage(canvas.toDataURL("image/png"), "PNG", 0, 0, w, Math.min(h, 297));
      pdf.save(`scheda-${card.name || "personaggio"}.pdf`);
      toast.success("Scheda A4 generata");
    } catch (e) { toast.error("Generazione scheda fallita"); }
    finally { setBusy(false); }
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
            <div className="mx-auto" style={{ width: 320, perspective: "1600px" }}>
              <motion.div
                className="relative preserve-3d"
                style={{ width: 320, aspectRatio: "2.5/3.5", transformStyle: "preserve-3d" }}
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

              <Button data-testid="share-btn" onClick={shareImage} disabled={busy} variant="outline"
                className="rounded-none border-border bg-transparent text-foreground hover:bg-secondary font-label text-[11px] tracking-wide transition-colors">
                <Download className="w-3.5 h-3.5 mr-1.5" /> IMMAGINE
              </Button>
              <Button data-testid="pdf-btn" onClick={exportPDF} disabled={busy} variant="outline"
                className="rounded-none border-border bg-transparent text-foreground hover:bg-secondary font-label text-[11px] tracking-wide transition-colors">
                <Printer className="w-3.5 h-3.5 mr-1.5" /> PDF F/R
              </Button>
            </div>
            {card.type === "character" && (
              <Button data-testid="sheet-btn" onClick={exportSheet} disabled={busy}
                className="w-full mt-2 rounded-none bg-gold text-obsidian hover:bg-gold-deep font-label text-[11px] tracking-widest transition-colors">
                <FileText className="w-3.5 h-3.5 mr-1.5" /> SCHEDA PERSONAGGIO A4
              </Button>
            )}
          </div>

          {/* Info */}
          <div className="space-y-6">
            <div>
              <p className="font-label text-xs tracking-[0.3em] text-gold/70 mb-2">{typeLabel(card.type, card.custom_type).toUpperCase()}</p>
              <h1 className="font-display text-4xl sm:text-5xl tf-gold-text">{card.name}</h1>
            </div>
            {card.description && (
              <p className="font-body text-lg text-foreground/85 italic leading-relaxed">{card.description}</p>
            )}
            {card.story && (
              <div className="border-l-2 border-gold-deep/60 pl-4">
                <p className="font-label text-[10px] tracking-widest text-gold/60 mb-1">STORIA</p>
                <p className="font-body text-foreground/75 leading-relaxed">{card.story}</p>
              </div>
            )}

            {card.type === "character" && <SpellSlots card={card} onUpdate={updateSlots} />}

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

      {/* Off-screen A4 character sheet for PDF */}
      {card.type === "character" && (
        <div style={{ position: "fixed", left: -9999, top: 0 }}>
          <CharacterSheet ref={sheetRef} card={card} />
        </div>
      )}
    </div>
  );
}

const CharacterSheet = React.forwardRef(({ card }, ref) => {
  const a = card.attributes || {};
  const img = card.artwork_path ? artworkUrl(card.artwork_path) : null;
  const scalarKeys = Object.keys(a).filter((k) => isScalar(a[k]) && a[k] !== "" && !ABILITIES.includes(k));
  const listKeys = Object.keys(a).filter((k) => Array.isArray(a[k]) && a[k].length && typeof a[k][0] === "string");
  return (
    <div ref={ref} style={{ width: 794, minHeight: 1123, background: "#fefdf9", color: "#1a140c", padding: 48, fontFamily: "'Spectral', serif" }}>
      <div style={{ borderBottom: "3px double #9a7d2e", paddingBottom: 16, marginBottom: 20, display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <div style={{ fontFamily: "'Cinzel', serif", fontSize: 12, letterSpacing: 3, color: "#9a7d2e" }}>SCHEDA PERSONAGGIO · TOMEFORGE</div>
          <div style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 44, fontWeight: 700, lineHeight: 1 }}>{card.name}</div>
          <div style={{ fontSize: 16, marginTop: 4 }}>{[a.razza, a.classe, a.livello && `Livello ${a.livello}`].filter(Boolean).join(" · ")}</div>
        </div>
        {img && <img src={img} alt="" crossOrigin="anonymous" style={{ width: 120, height: 120, objectFit: "cover", border: "2px solid #9a7d2e" }} />}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 10, marginBottom: 20 }}>
        {ABILITIES.map((k) => (
          <div key={k} style={{ border: "1.5px solid #9a7d2e", textAlign: "center", padding: "10px 4px" }}>
            <div style={{ fontFamily: "'Cinzel', serif", fontSize: 11, letterSpacing: 1, color: "#7a5c1e" }}>{k.toUpperCase()}</div>
            <div style={{ fontSize: 26, fontWeight: 600 }}>{a[k] || "—"}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div>
          {scalarKeys.map((k) => (
            <div key={k} style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #d8c9a0", padding: "6px 0" }}>
              <span style={{ fontFamily: "'Cinzel', serif", fontSize: 11, letterSpacing: 1, color: "#7a5c1e", textTransform: "uppercase" }}>{attrLabel(k)}</span>
              <span style={{ fontSize: 14 }}>{a[k]}</span>
            </div>
          ))}
        </div>
        <div>
          {listKeys.map((k) => (
            <div key={k} style={{ marginBottom: 14 }}>
              <div style={{ fontFamily: "'Cinzel', serif", fontSize: 12, letterSpacing: 1, color: "#7a5c1e", textTransform: "uppercase", marginBottom: 4, borderBottom: "1px solid #9a7d2e" }}>{attrLabel(k)}</div>
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {a[k].filter((x) => String(x).trim()).map((it, i) => <li key={i} style={{ fontSize: 14, marginBottom: 3 }}>{it}</li>)}
              </ul>
            </div>
          ))}
          {Array.isArray(a.slot_incantesimi) && a.slot_incantesimi.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontFamily: "'Cinzel', serif", fontSize: 12, letterSpacing: 1, color: "#7a5c1e", textTransform: "uppercase", marginBottom: 4, borderBottom: "1px solid #9a7d2e" }}>Slot Incantesimi</div>
              {a.slot_incantesimi.map((s, i) => (
                <div key={i} style={{ fontSize: 14 }}>Livello {s.livello || i + 1}: {s.totale} slot</div>
              ))}
            </div>
          )}
        </div>
      </div>

      {card.description && <p style={{ fontStyle: "italic", marginTop: 20, fontSize: 14 }}>{card.description}</p>}
      {card.story && <p style={{ marginTop: 10, fontSize: 13, color: "#4a3c28" }}>{card.story}</p>}
    </div>
  );
});
CharacterSheet.displayName = "CharacterSheet";
