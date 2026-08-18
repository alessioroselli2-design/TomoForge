import React, { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Search, Plus, Printer, Check, X, Loader2 } from "lucide-react";
import { toast } from "sonner";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import { api } from "@/lib/api";
import { CARD_TYPES } from "@/lib/cardTypes";
import Navbar from "@/components/Navbar";
import { CardFront } from "@/components/TradingCard";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const EMPTY_IMG = "https://images.pexels.com/photos/7978240/pexels-photo-7978240.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";

export default function Collection() {
  const navigate = useNavigate();
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

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
          <h1 className="font-display text-4xl sm:text-5xl tf-gold-text">La Collezione</h1>
        </motion.div>

        {/* Controls */}
        <div className="mt-8 flex flex-col lg:flex-row gap-4 lg:items-center lg:justify-between">
          <div className="relative w-full lg:max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input data-testid="search-input" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Cerca per nome…"
              className="pl-9 bg-input border-border rounded-none font-body focus-visible:ring-gold" />
          </div>
        </div>

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
              {cards.map((card, i) => (
                <motion.button
                  key={card.id}
                  data-testid={`card-${card.id}`}
                  onClick={() => navigate(`/carta/${card.id}`)}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: Math.min(i * 0.04, 0.5) }}
                  whileHover={{ y: -6 }}
                  className="text-left group"
                  style={{ aspectRatio: "2.5/3.5" }}
                >
                  <div className="w-full h-full transition-shadow duration-300 group-hover:shadow-[0_14px_40px_-8px_rgba(212,175,55,0.35)]">
                    <CardFront card={card} />
                  </div>
                </motion.button>
              ))}
            </div>
          )}
        </div>
      </main>
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
