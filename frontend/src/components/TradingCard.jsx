import React from "react";
import { QRCodeCanvas } from "qrcode.react";
import { Flame, Skull, Sword, Moon, Eye, Shield, Star, Sparkles } from "lucide-react";
import { artworkUrl } from "@/lib/api";
import { typeLabel, typeIcon, attrLabel, QUICK_FIELDS } from "@/lib/cardTypes";
import { useI18n } from "@/lib/i18n";

const EMBLEM_ICONS = {
  flame: Flame, skull: Skull, dragon: Sparkles, sword: Sword,
  moon: Moon, eye: Eye, shield: Shield, star: Star,
};

const PLACEHOLDER = "https://images.unsplash.com/photo-1769221909977-dafd61c79a3d?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDF8MHwxfHNlYXJjaHwxfHxkYXJrJTIwZmFudGFzeSUyMGNoYXJhY3RlciUyMHBvcnRyYWl0fGVufDB8fHx8MTc4NzAzMjcyOXww&ixlib=rb-4.1.0&q=85";

const isScalar = (v) => typeof v === "string" || typeof v === "number";

const ABIL = ["for", "des", "cos", "int", "sag", "car"];

// Compact gameplay quick-reference shown on the card FRONT.
const QuickStats = ({ card }) => {
  const attrs = card.attributes || {};
  const has = (k) => isScalar(attrs[k]) && String(attrs[k]).trim() !== "";
  const showAbil = (card.type === "monster" || card.type === "character") && ABIL.some(has);

  let fields = (QUICK_FIELDS[card.type] || []).filter(has);
  if (!fields.length && !showAbil) {
    fields = Object.keys(attrs).filter((k) => has(k) && !ABIL.includes(k)).slice(0, 4);
  }
  fields = fields.slice(0, 6);

  if (!showAbil && !fields.length) return null;
  return (
    <div className="mt-2 space-y-1.5">
      {showAbil && (
        <div className="grid grid-cols-6 gap-1">
          {ABIL.filter(has).map((k) => (
            <div key={k} className="text-center border border-gold-deep/40 bg-obsidian/60 py-1">
              <div className="font-label text-[8px] tracking-wider text-gold/70 uppercase">{k}</div>
              <div className="font-body text-[11px] text-foreground leading-none mt-0.5">{attrs[k]}</div>
            </div>
          ))}
        </div>
      )}
      {fields.length > 0 && (
        <div className="grid grid-cols-2 gap-1">
          {fields.map((k) => (
            <div key={k} className="border border-gold-deep/30 bg-obsidian/50 px-1.5 py-1 leading-tight">
              <div className="font-label text-[7px] tracking-wider text-gold/60 uppercase truncate">{attrLabel(k)}</div>
              <div className="font-body text-[10px] text-foreground/90 truncate">{attrs[k]}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export const CardFront = React.forwardRef(({ card, exportMode, imgUrl }, ref) => {
  const { t } = useI18n();
  const TypeIcon = typeIcon(card.type);
  const img = imgUrl || (card.artwork_path ? artworkUrl(card.artwork_path) : PLACEHOLDER);
  const qrValue = `${window.location.origin}/p/${card.id}`;
  const frame = card.frame || "gold";
  return (
    <div ref={ref} data-testid="card-front"
      className={`relative w-full h-full bg-card tf-card-frame tf-foil-${frame} flex flex-col overflow-hidden ${exportMode ? "tf-export-card" : ""}`}>
      {/* header */}
      <div className="flex-none flex items-center justify-between px-3 pt-3 pb-1.5">
        <h3 className={`font-heading font-bold text-lg leading-tight truncate pr-2 tf-title-3d ${exportMode ? "text-gold" : "tf-gold-text"}`}>{card.name || "Senza nome"}</h3>
        <div className="flex items-center gap-1 shrink-0">
          <TypeIcon className="w-3.5 h-3.5 text-gold" />
          <span className="font-label text-[9px] tracking-widest text-gold/80 uppercase">{typeLabel(card.type, card.custom_type)}</span>
        </div>
      </div>
      <hr className="tf-divider mx-3" aria-hidden="true" />
      {/* artwork */}
      <div className="flex-none mx-3 mt-2 border border-gold-deep/60 overflow-hidden bg-obsidian" style={{ aspectRatio: "1.35" }}>
        <img src={img} alt={card.name} className="w-full h-full object-cover" crossOrigin="anonymous" />
      </div>
      {/* body */}
      <div className="min-h-0 flex-1 px-3 py-2 overflow-hidden">
        <QuickStats card={card} />
        {card.description && (
          <p className="font-body text-[10px] leading-snug text-foreground/70 mt-1.5 line-clamp-2 italic">{card.description}</p>
        )}
      </div>
      {/* footer with QR */}
      <div className="flex-none flex items-end justify-between px-3 pb-2.5 pt-1">
        <span className="font-label text-[8px] tracking-widest text-muted-foreground uppercase leading-tight">{t("completeDetails")}<br/>→</span>
        <div className="bg-white p-1 border border-gold-deep absolute right-2.5 bottom-2.5">
          <QRCodeCanvas value={qrValue} size={40} bgColor="#ffffff" fgColor="#0c0a09" level="M" />
        </div>
      </div>
    </div>
  );
});
CardFront.displayName = "CardFront";

export const CardBack = React.forwardRef(({ card, exportMode }, ref) => {
  const back = card.back || {};
  const Emblem = EMBLEM_ICONS[back.emblem] || Flame;
  const color = back.color || "#7f1d1d";
  return (
    <div ref={ref} data-testid="card-back"
      className={`relative w-full h-full bg-card tf-card-frame tf-foil-${card.frame || "gold"} flex flex-col items-center justify-center overflow-hidden p-6`}>
      <div className="absolute inset-3 border border-gold-deep/50" aria-hidden="true" />
      <div className="absolute inset-5 border border-gold-deep/25" aria-hidden="true" />
      {back.style === "runic" && (
        <div className="absolute inset-0 opacity-[0.06] flex items-center justify-center font-display text-[10rem] text-gold pointer-events-none">ᛟ</div>
      )}
      <div className="relative z-10 flex flex-col items-center text-center gap-5">
        <div className="w-24 h-24 rounded-full flex items-center justify-center border-2"
          style={{ borderColor: color, boxShadow: `0 0 30px ${color}55` }}>
          <Emblem className="w-11 h-11" style={{ color }} />
        </div>
        <div className={`font-display text-2xl tracking-wide tf-title-3d ${exportMode ? "text-gold" : "tf-gold-text"}`}>TOMEFORGE</div>
        {back.motto && (
          <p className="font-heading italic text-lg text-foreground/80 max-w-[80%]">“{back.motto}”</p>
        )}
        <hr className="tf-divider w-32" aria-hidden="true" />
        <span className="font-label text-[9px] tracking-[0.3em] text-gold/60 uppercase">{typeLabel(card.type, card.custom_type)}</span>
      </div>
    </div>
  );
});
CardBack.displayName = "CardBack";
