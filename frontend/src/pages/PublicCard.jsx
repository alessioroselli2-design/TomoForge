import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { BookOpen, Loader2, ScrollText } from "lucide-react";
import { API, publicArtworkUrl } from "@/lib/api";
import { typeLabel, attrLabel } from "@/lib/cardTypes";
import { CardFront } from "@/components/TradingCard";

const ABIL = ["for", "des", "cos", "int", "sag", "car"];
const isScalar = (v) => typeof v === "string" || typeof v === "number";

const Attributes = ({ attrs }) => {
  const abil = ABIL.filter((k) => attrs[k] !== undefined && String(attrs[k]).trim() !== "");
  const scalarKeys = Object.keys(attrs).filter((k) => isScalar(attrs[k]) && String(attrs[k]).trim() !== "" && !ABIL.includes(k));
  const listKeys = Object.keys(attrs).filter((k) => Array.isArray(attrs[k]) && attrs[k].length && typeof attrs[k][0] === "string");
  const objListKeys = Object.keys(attrs).filter((k) => Array.isArray(attrs[k]) && attrs[k].length && typeof attrs[k][0] === "object");
  return (
    <div className="border border-gold-deep/50 bg-card p-6">
      {abil.length > 0 && (
        <div className="grid grid-cols-6 gap-2 mb-5">
          {abil.map((k) => (
            <div key={k} className="text-center border border-gold-deep/40 bg-obsidian/50 py-2">
              <div className="font-label text-[10px] tracking-widest text-gold uppercase">{k}</div>
              <div className="font-body text-lg text-foreground">{attrs[k]}</div>
            </div>
          ))}
        </div>
      )}
      <div className="space-y-1.5">
        {scalarKeys.map((k) => (
          <div key={k} className="flex gap-2 text-sm border-b border-border/50 pb-1.5">
            <span className="font-label text-xs tracking-wide text-gold/80 uppercase min-w-[130px]">{attrLabel(k)}</span>
            <span className="font-body text-foreground/90">{attrs[k]}</span>
          </div>
        ))}
      </div>
      {listKeys.map((k) => (
        <div key={k} className="mt-4">
          <div className="font-label text-xs tracking-widest text-gold uppercase mb-2">{attrLabel(k)}</div>
          <ul className="list-disc list-inside space-y-1">
            {attrs[k].filter((x) => String(x).trim()).map((it, i) => <li key={i} className="font-body text-sm text-foreground/90">{it}</li>)}
          </ul>
        </div>
      ))}
      {objListKeys.map((k) => (
        <div key={k} className="mt-4">
          <hr className="tf-divider-red mb-3" aria-hidden="true" />
          <div className="font-label text-xs tracking-widest text-gold uppercase mb-2">{attrLabel(k)}</div>
          <div className="space-y-2">
            {attrs[k].map((obj, i) => (
              <div key={i} className="font-body text-sm">
                <span className="font-semibold text-gold/90">{obj.nome || obj.name || `Liv. ${obj.livello}`}{(obj.nome || obj.name) ? ". " : ": "}</span>
                <span className="text-foreground/85">{obj.descrizione || obj.description || (obj.totale ? `${obj.totale} slot` : "")}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export default function PublicCard() {
  const { id } = useParams();
  const [card, setCard] = useState(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API}/public/cards/${id}`);
        if (!res.ok) throw new Error("not found");
        setCard(await res.json());
      } catch (e) {
        setNotFound(true);
      }
    })();
  }, [id]);

  if (notFound) {
    return (
      <div className="min-h-screen bg-obsidian tf-noise flex flex-col items-center justify-center px-6 text-center">
        <ScrollText className="w-10 h-10 text-gold/60 mb-4" />
        <h1 className="font-heading text-3xl text-foreground">Pergamena introvabile</h1>
        <p className="font-body text-muted-foreground mt-2">Questa carta non esiste o è stata dissolta.</p>
        <Link to="/" className="mt-6 font-label text-xs tracking-widest text-gold border border-gold-deep/50 px-5 py-2.5 hover:bg-secondary transition-colors">VAI A TOMEFORGE</Link>
      </div>
    );
  }

  if (!card) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-gold animate-spin" />
      </div>
    );
  }

  const hasAttrs = Object.keys(card.attributes || {}).length > 0;

  return (
    <div className="min-h-screen bg-obsidian tf-noise">
      <header className="border-b border-gold-deep/30 bg-obsidian/90 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-4 sm:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group">
            <BookOpen className="w-6 h-6 text-gold" strokeWidth={1.5} />
            <span className="font-label tracking-[0.3em] text-gold text-sm">TOMEFORGE</span>
          </Link>
          <span className="font-label text-[10px] tracking-widest text-muted-foreground uppercase">Carta condivisa</span>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-8 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
            className="mx-auto lg:mx-0" style={{ width: 300, aspectRatio: "2.5/3.5" }}>
            <CardFront card={card} imgUrl={publicArtworkUrl(card.artwork_path)} />
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.1 }}
            className="space-y-6">
            <div>
              <p className="font-label text-xs tracking-[0.3em] text-gold/70 mb-2">{typeLabel(card.type, card.custom_type).toUpperCase()}</p>
              <h1 className="font-display text-4xl sm:text-5xl tf-gold-text">{card.name}</h1>
            </div>
            {card.description && <p className="font-body text-lg text-foreground/85 italic leading-relaxed">{card.description}</p>}
            {card.story && (
              <div className="border-l-2 border-gold-deep/60 pl-4">
                <p className="font-label text-[10px] tracking-widest text-gold/60 mb-1">STORIA</p>
                <p className="font-body text-foreground/75 leading-relaxed">{card.story}</p>
              </div>
            )}
            {hasAttrs && <Attributes attrs={card.attributes} />}
          </motion.div>
        </div>

        <div className="mt-12 text-center">
          <Link to="/" className="font-label text-xs tracking-widest text-gold hover:text-gold-deep border border-gold-deep/50 px-6 py-3 inline-block transition-colors">
            CREA LE TUE CARTE SU TOMEFORGE
          </Link>
        </div>
      </main>
    </div>
  );
}
