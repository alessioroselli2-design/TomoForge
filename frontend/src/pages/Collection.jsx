import React, { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Search, Plus, Printer, Check, CheckCheck, Layers, RotateCw, X, Loader2 } from "lucide-react";
import { toast } from "sonner";
import jsPDF from "jspdf";
import { api } from "@/lib/api";
import { CARD_TYPES } from "@/lib/cardTypes";
import Navbar from "@/components/Navbar";
import { CardFront } from "@/components/TradingCard";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n";
import { addPrintSheetCard } from "@/lib/cardExport";
import { getPrintSheetPositions, PRINT_FORMATS } from "@/lib/printFormats";

const EMPTY_IMG = "https://images.pexels.com/photos/7978240/pexels-photo-7978240.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";

export default function Collection() {
  const navigate = useNavigate();
  const { t } = useI18n();
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [selectMode, setSelectMode] = useState(false);
  const [selected, setSelected] = useState([]);
  const [exporting, setExporting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [format, setFormat] = useState("standard");
  const [includeBack, setIncludeBack] = useState(false);
  const cardRefs = useRef({});
  const sheetContainerRef = useRef(null);

  const toggleSelect = (id) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const selectAll = () => setSelected(cards.map((c) => c.id));

  const exitSelectMode = () => {
    setSelectMode(false);
    setSelected([]);
  };

  const chosenCards = cards.filter((c) => selected.includes(c.id));
  const totalSteps = chosenCards.length * (includeBack ? 2 : 1);
  const perPage = PRINT_FORMATS[format].cols * PRINT_FORMATS[format].rows;

  const exportPrintSheet = async () => {
    if (!chosenCards.length) {
      toast.error("Seleziona almeno una carta");
      return;
    }
    setExporting(true);
    const { w: cardW, h: cardH, cols, rows } = PRINT_FORMATS[format];
    const perPage = cols * rows;
    const drawCut = (pdf, x, y) => {
      // faint card boundary
      pdf.setDrawColor(120, 100, 50);
      pdf.setLineWidth(0.1);
      pdf.rect(x, y, cardW, cardH);
      // corner crop/trim marks (L-shaped, pointing outward) for precise cutting
      const L = 3, o = 0.6;
      pdf.setDrawColor(60, 50, 25);
      pdf.setLineWidth(0.2);
      const marks = [
        // top-left
        [x - o - L, y, x - o, y], [x, y - o - L, x, y - o],
        // top-right
        [x + cardW + o, y, x + cardW + o + L, y], [x + cardW, y - o - L, x + cardW, y - o],
        // bottom-left
        [x - o - L, y + cardH, x - o, y + cardH], [x, y + cardH + o, x, y + cardH + o + L],
        // bottom-right
        [x + cardW + o, y + cardH, x + cardW + o + L, y + cardH], [x + cardW, y + cardH + o, x + cardW, y + cardH + o + L],
      ];
      marks.forEach(([x1, y1, x2, y2]) => pdf.line(x1, y1, x2, y2));
    };
    try {
      const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
      const pages = Math.ceil(chosenCards.length / perPage);
      let step = 0;
      let firstPage = true;

      for (let p = 0; p < pages; p++) {
        const group = chosenCards.slice(p * perPage, (p + 1) * perPage);
        if (!firstPage) pdf.addPage();
        firstPage = false;
        // Front page
        for (let i = 0; i < group.length; i++) {
          step += 1; setProgress(step);
          const el = cardRefs.current[group[i].id];
          if (!el) continue;
           const { x, y } = getPrintSheetPositions(format, group.length)[i];
           await addPrintSheetCard(pdf, el, group[i], { x, y, w: cardW, h: cardH });
           drawCut(pdf, x, y);
        }
        // Mirrored back page for duplex printing
        if (includeBack) {
          pdf.addPage();
          for (let i = 0; i < group.length; i++) {
            step += 1; setProgress(step);
             const { x, y } = getPrintSheetPositions(format, group.length, true)[i];
             await addPrintSheetCard(pdf, null, group[i], { x, y, w: cardW, h: cardH }, true);
            drawCut(pdf, x, y);
          }
        }
      }
      pdf.save(`tomeforge-foglio-stampa.pdf`);
      toast.success(`Foglio pronto: ${chosenCards.length} carte`);
      exitSelectMode();
    } catch (e) {
      toast.error("Generazione foglio fallita");
    } finally {
      setExporting(false);
      setProgress(0);
    }
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filter !== "all") params.type = filter;
      if (search.trim()) params.search = search.trim();
      const res = await api.get("/cards", { params });
      setCards(res.data);
    } catch (e) {
      toast.error("Impossibile caricare la collezione");
    } finally {
      setLoading(false);
    }
  }, [filter, search]);

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  return (
    <div className="min-h-screen bg-obsidian">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-8 py-10">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
          <p className="font-label text-xs tracking-[0.3em] text-gold/70 mb-2">IL TUO GRIMORIO</p>
          <h1 className="font-display text-4xl sm:text-5xl tf-gold-text tf-title-3d">{t("collection")}</h1>
        </motion.div>

        {/* Controls */}
        <div className="mt-8 flex flex-col lg:flex-row gap-4 lg:items-center lg:justify-between">
          <div className="relative w-full lg:max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input data-testid="search-input" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Cerca per nome…"
              className="pl-9 bg-input border-border rounded-none font-body focus-visible:ring-gold" />
          </div>
          <div className="flex items-center gap-2">
            {!selectMode ? (
              <Button data-testid="print-sheet-toggle" onClick={() => setSelectMode(true)} variant="outline"
                className="rounded-none border-gold-deep/50 bg-transparent text-gold hover:bg-secondary font-label text-[11px] tracking-widest h-9 transition-colors">
                <Printer className="w-4 h-4 mr-1.5" /> {t("printSheet").toUpperCase()}
              </Button>
            ) : (
              <Button data-testid="print-sheet-cancel" onClick={exitSelectMode} variant="outline"
                className="rounded-none border-border bg-transparent text-muted-foreground hover:text-crimson font-label text-[11px] tracking-widest h-9 transition-colors">
                <X className="w-4 h-4 mr-1.5" /> ANNULLA
              </Button>
            )}
          </div>
        </div>

        {selectMode && (
          <div data-testid="select-hint" className="mt-3 border border-gold-deep/40 bg-card p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="font-body text-sm text-foreground/80">
                Tocca le carte da includere · <span className="text-gold">{selected.length}</span> selezionate
              </span>
              <div className="flex items-center gap-2">
                <Button size="sm" variant="outline" data-testid="select-all-btn" onClick={selectAll}
                  className="rounded-none border-gold-deep/50 bg-transparent text-gold hover:bg-secondary font-label text-[10px] tracking-widest h-8 transition-colors">
                  <CheckCheck className="w-3.5 h-3.5 mr-1" /> {t("selectAll").toUpperCase()}
                </Button>
                <Button size="sm" variant="outline" data-testid="deselect-all-btn" onClick={() => setSelected([])}
                  className="rounded-none border-border bg-transparent text-muted-foreground hover:text-crimson font-label text-[10px] tracking-widest h-8 transition-colors">
                  <X className="w-3.5 h-3.5 mr-1" /> {t("deselectAll").toUpperCase()}
                </Button>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-x-6 gap-y-3 pt-1 border-t border-border/50">
              <div className="flex items-center gap-2 pt-2">
                <span className="font-label text-[10px] tracking-widest text-gold/70 flex items-center gap-1"><Layers className="w-3.5 h-3.5" /> {t("format").toUpperCase()}</span>
                {Object.entries(PRINT_FORMATS).map(([id, f]) => (
                  <button key={id} data-testid={`format-${id}`} onClick={() => setFormat(id)}
                    className={`px-3 py-1 rounded-none border font-label text-[10px] tracking-widest uppercase transition-colors ${format === id ? "bg-gold text-obsidian border-gold" : "border-border text-muted-foreground hover:text-gold hover:border-gold-deep"}`}>
                    {f.label} <span className="opacity-60">{f.cols * f.rows}/pag</span>
                  </button>
                ))}
              </div>
              <button data-testid="include-back-toggle" onClick={() => setIncludeBack((v) => !v)}
                className={`mt-2 flex items-center gap-2 px-3 py-1 rounded-none border font-label text-[10px] tracking-widest uppercase transition-colors ${includeBack ? "bg-gold text-obsidian border-gold" : "border-border text-muted-foreground hover:text-gold hover:border-gold-deep"}`}>
                <RotateCw className="w-3.5 h-3.5" /> {includeBack ? "RETRO INCLUSO (F/R)" : "INCLUDI RETRO (F/R)"}
              </button>
            </div>
            <p className="font-body text-xs text-muted-foreground/80 border-t border-border/40 pt-2">
              Il PDF mantiene le dimensioni fisiche selezionate: {PRINT_FORMATS[format].cols}×{PRINT_FORMATS[format].rows} carte per A4.
              {selected.length < perPage && " Le posizioni non selezionate restano bianche: seleziona altre carte per riempire la griglia."}
              {includeBack && " Per allineare fronte e retro, stampa in modalità fronte/retro con ribaltamento sul lato lungo."}
            </p>
          </div>
        )}

        {/* Type filters */}
        <div className="mt-4 flex flex-wrap gap-2">
          <FilterChip active={filter === "all"} onClick={() => setFilter("all")} label="Tutte" testid="filter-all" />
          {CARD_TYPES.map((t) => (
            <FilterChip key={t.id} active={filter === t.id} onClick={() => setFilter(t.id)} label={t.label} Icon={t.icon} testid={`filter-${t.id}`} />
          ))}
        </div>

        {/* Grid */}
        <div className="mt-10">
          {loading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-6">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="bg-card border border-border animate-pulse" style={{ aspectRatio: "2.5/3.5" }} />
              ))}
            </div>
          ) : cards.length === 0 ? (
            <EmptyState navigate={navigate} search={search} filter={filter} />
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-6">
              {cards.map((card, i) => {
                const isSel = selected.includes(card.id);
                return (
                  <motion.button
                    key={card.id}
                    data-testid={`card-${card.id}`}
                    onClick={() => (selectMode ? toggleSelect(card.id) : navigate(`/carta/${card.id}`))}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: Math.min(i * 0.04, 0.5) }}
                    whileHover={{ y: -6 }}
                    className="text-left group relative touch-manipulation"
                    style={{ aspectRatio: "2.5/3.5" }}
                  >
                    <div className={`w-full h-full transition-shadow duration-300 group-hover:shadow-[0_14px_40px_-8px_rgba(212,175,55,0.35)] ${selectMode && isSel ? "ring-2 ring-gold" : ""} ${selectMode && !isSel ? "opacity-70" : ""}`}>
                      <CardFront card={card} />
                    </div>
                    {selectMode && (
                      <div className={`absolute top-2 right-2 w-7 h-7 flex items-center justify-center border-2 transition-colors ${isSel ? "bg-gold border-gold" : "bg-obsidian/70 border-gold-deep/60"}`}>
                        {isSel && <Check className="w-4 h-4 text-obsidian" />}
                      </div>
                    )}
                  </motion.button>
                );
              })}
            </div>
          )}
        </div>
      </main>

      {/* Floating export bar */}
      {selectMode && selected.length > 0 && (
        <motion.div
          initial={{ y: 80, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
          className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4 bg-card border border-gold-deep px-5 py-3 shadow-2xl shadow-black/60">
          <span className="font-label text-xs tracking-widest text-gold">{selected.length} SELEZIONATE</span>
          <Button data-testid="export-sheet-btn" onClick={exportPrintSheet} disabled={exporting}
            className="rounded-none bg-gold text-obsidian hover:bg-gold-deep font-label text-xs tracking-widest h-9 transition-colors">
            {exporting ? <Loader2 className="w-4 h-4 mr-1.5 animate-spin" /> : <Printer className="w-4 h-4 mr-1.5" />}
            {exporting ? `${progress}/${totalSteps}` : t("exportPdf").toUpperCase()}
          </Button>
        </motion.div>
      )}

      {/* Off-screen render of selected cards for capture */}
      <div ref={sheetContainerRef} style={{ position: "fixed", left: -99999, top: 0 }} aria-hidden="true">
        {chosenCards.map((card) => (
          <div key={card.id}>
            <div ref={(el) => { if (el) cardRefs.current[card.id] = el; }} style={{ width: 340, height: 476, marginBottom: 8 }}>
              <CardFront card={card} exportMode />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const FilterChip = ({ active, onClick, label, Icon, testid }) => (
  <button data-testid={testid} onClick={onClick}
    className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-none border font-label text-[11px] tracking-widest uppercase transition-colors ${active ? "bg-gold text-obsidian border-gold" : "bg-transparent text-muted-foreground border-border hover:border-gold-deep hover:text-gold"}`}>
    {Icon && <Icon className="w-3.5 h-3.5" />} {label}
  </button>
);

const EmptyState = ({ navigate, search, filter }) => (
  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
    className="flex flex-col items-center text-center py-16 border border-dashed border-gold-deep/30 bg-card/40">
    <img src={EMPTY_IMG} alt="Grimorio vuoto" className="w-48 h-32 object-cover mb-6 opacity-70 border border-gold-deep/40" />
    <h3 className="font-heading text-2xl text-foreground">
      {search || filter !== "all" ? "Nessuna carta trovata" : "Il tuo tomo è ancora vuoto"}
    </h3>
    <p className="font-body text-muted-foreground mt-2 max-w-md">
      {search || filter !== "all" ? "Prova a modificare i filtri o la ricerca." : "Evoca la tua prima carta e dai vita alle tue leggende."}
    </p>
    <Button data-testid="empty-create" onClick={() => navigate("/crea")}
      className="mt-6 rounded-none bg-gold text-obsidian hover:bg-gold-deep font-label tracking-widest transition-colors">
      <Plus className="w-4 h-4 mr-1.5" /> CREA UNA CARTA
    </Button>
  </motion.div>
);
