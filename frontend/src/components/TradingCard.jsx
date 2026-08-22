import React from "react";
import { QRCodeCanvas } from "qrcode.react";
import { Flame, Skull, Sword, Moon, Eye, Shield, Star, Sparkles } from "lucide-react";
import { artworkUrl } from "@/lib/api";
import {
  typeLabel, typeIcon, attrLabel, QUICK_FIELDS, DEFAULT_APPEARANCE, FRAME_STYLES, TITLE_EFFECTS,
} from "@/lib/cardTypes";
import { useI18n } from "@/lib/i18n";

const EMBLEM_ICONS = {
  flame: Flame, skull: Skull, dragon: Sparkles, sword: Sword,
  moon: Moon, eye: Eye, shield: Shield, star: Star,
};

const PLACEHOLDER = "https://images.unsplash.com/photo-1769221909977-dafd61c79a3d?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDF8MHwxfHNlYXJjaHwxfHxkYXJrJTIwZmFudGFzeSUyMGNoYXJhY3RlciUyMHBvcnRyYWl0fGVufDB8fHx8MTc4NzAzMjcyOXww&ixlib=rb-4.1.0&q=85";

const isScalar = (v) => typeof v === "string" || typeof v === "number";

const ABIL = ["for", "des", "cos", "int", "sag", "car"];

const getFrameColors = (frame, appearance = {}) => {
  if (appearance.frame_custom_color_enabled) {
    return [appearance.frame_custom_color || "#d4af37", "#ffffff", appearance.frame_custom_color || "#d4af37"];
  }
  return FRAME_STYLES.find((style) => style.id === frame)?.colors || FRAME_STYLES[0].colors;
};

const sourceLabel = (sources = []) => sources
  .map((source) => `${source.filename || "Manuale"} · p.${source.page || "?"}`)
  .filter((source, index, all) => all.indexOf(source) === index)
  .join(" | ");

const ruleSourceLabel = (rules = []) => rules
  .map((rule) => `${rule.name || "Regola"} — ${sourceLabel(rule.source_refs || [])}`)
  .filter((rule, index, all) => all.indexOf(rule) === index)
  .join(" | ");

const foilFrameStyle = (frame, appearance) => {
  const colors = getFrameColors(frame, appearance);
  const primary = colors[0];
  const highlight = colors[Math.floor(colors.length / 2)] || primary;
  const accent = colors[colors.length - 1] || primary;
  return {
    "--tf-frame-primary": primary,
    "--tf-frame-highlight": highlight,
    "--tf-frame-accent": accent,
    borderImageSource: `linear-gradient(135deg, ${colors.join(", ")})`,
    borderImageSlice: 1,
    boxShadow: `inset 0 0 0 2px ${highlight}2e, inset 0 0 35px rgba(0,0,0,.68), 0 0 14px ${highlight}55`,
  };
};

// Compact gameplay quick-reference shown on the card FRONT.
const QuickStats = ({ card, exportMode }) => {
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
                <div className={`font-label text-[8px] tracking-wider uppercase ${exportMode ? "tf-export-stat-label" : "text-gold/70"}`}>{k}</div>
                <div className={`font-body text-[11px] leading-none mt-0.5 ${exportMode ? "tf-export-stat-value" : "text-foreground"}`}>{attrs[k]}</div>
            </div>
          ))}
        </div>
      )}
      {fields.length > 0 && (
        <div className="grid grid-cols-2 gap-1">
          {fields.map((k) => (
            <div key={k} className="border border-gold-deep/30 bg-obsidian/50 px-1.5 py-1 leading-tight">
              <div className={`font-label text-[7px] tracking-wider uppercase ${exportMode ? "tf-export-stat-label" : "text-gold/60 truncate"}`}>{attrLabel(k)}</div>
              <div className={`font-body text-[10px] ${exportMode ? "tf-export-stat-value" : "text-foreground/90 truncate"}`}>{attrs[k]}</div>
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
  const appearance = { ...DEFAULT_APPEARANCE, ...(card.appearance || {}) };
  const titleEffect = TITLE_EFFECTS.find((effect) => effect.id === appearance.title_effect) || TITLE_EFFECTS[0];
  const titleColors = appearance.title_custom_color_enabled
    ? [appearance.title_custom_color, appearance.title_custom_color, appearance.title_custom_color]
    : titleEffect.colors;
  const frontBackground = appearance.front_background_gradient
    ? `linear-gradient(145deg, ${appearance.front_background_start}, ${appearance.front_background_end})`
    : appearance.front_background_start;
  return (
    <div ref={ref} data-testid="card-front"
      className={`relative w-full h-full tf-card-front tf-card-frame flex flex-col overflow-hidden ${exportMode ? "tf-export-card" : ""}`}
      style={{
        ...foilFrameStyle(frame, appearance),
        background: frontBackground,
        "--tf-description-opacity": appearance.description_opacity,
        "--tf-description-color": appearance.text_panel_color,
        "--tf-description-text": appearance.text_color,
      }}>
      <div className="tf-front-inner-border" aria-hidden="true" />
      <div className="tf-front-corner tf-front-corner-tl" aria-hidden="true">✦</div>
      <div className="tf-front-corner tf-front-corner-tr" aria-hidden="true">✦</div>
      <div className="tf-front-corner tf-front-corner-bl" aria-hidden="true">✦</div>
      <div className="tf-front-corner tf-front-corner-br" aria-hidden="true">✦</div>
      {/* header */}
      <div className="relative z-10 flex-none flex items-center justify-between px-3 pt-3 pb-1.5">
        <h3
          className={`min-w-0 font-heading font-bold text-lg leading-tight pr-2 tf-title-metal ${appearance.title_shadow ? "tf-title-shadow" : "tf-title-flat"} ${exportMode ? "tf-export-title" : "truncate"}`}
          style={{ backgroundImage: `linear-gradient(180deg, ${titleColors.join(", ")})` }}
        >
          {card.name || "Senza nome"}
        </h3>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`font-label hidden min-[250px]:block text-[8px] tracking-widest uppercase ${exportMode ? "tf-export-stat-label" : "text-gold/80"}`}>
            {typeLabel(card.type, card.custom_type)}
          </span>
          <div className="tf-type-seal" title={typeLabel(card.type, card.custom_type)} aria-label={typeLabel(card.type, card.custom_type)}>
            <TypeIcon className="h-4 w-4" strokeWidth={1.8} />
          </div>
        </div>
      </div>
      <hr className="tf-divider mx-3" aria-hidden="true" />
      {/* artwork */}
      <div className="flex-none mx-3 mt-2 border border-gold-deep/60 overflow-hidden bg-obsidian" style={{ aspectRatio: "1.35" }}>
        <img src={img} alt={card.name} className="w-full h-full object-cover" crossOrigin="anonymous" />
      </div>
      {/* body */}
      <div className="min-h-0 flex-1 px-3 py-2 overflow-hidden">
        <QuickStats card={card} exportMode={exportMode} />
        {card.description && (
          <div className="tf-description-panel">
            <p className={`font-body text-[10px] italic ${exportMode ? "tf-export-description" : "text-foreground/90 leading-snug line-clamp-2 pr-12"}`}>{card.description}</p>
          </div>
        )}
        {(card.rule_sources?.length > 0 || card.source_refs?.length > 0) && (
          <p className={`relative z-10 mt-1 px-3 pb-2 font-label text-[7px] tracking-wide ${exportMode ? "tf-export-stat-label" : "text-sky-100/75"}`}>
            FONTE · {card.rule_sources?.length ? ruleSourceLabel(card.rule_sources) : sourceLabel(card.source_refs)}
          </p>
        )}
      </div>
      {/* footer with QR */}
      <div className="relative flex min-h-[52px] flex-none items-end justify-between px-3 pb-2.5 pt-1">
        <span className={`font-label text-[8px] tracking-widest uppercase leading-tight ${exportMode ? "tf-export-footer" : "text-muted-foreground"}`}>{t("completeDetails")}<br/>→</span>
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
  const style = back.style || "classic";
  const appearance = { ...DEFAULT_APPEARANCE, ...(card.appearance || {}) };
  return (
    <div ref={ref} data-testid="card-back"
      className={`relative w-full h-full bg-card tf-card-frame tf-back-card tf-back-${style} flex flex-col items-center justify-center overflow-hidden p-6`}
      style={{
        ...foilFrameStyle(card.frame || "gold", appearance),
        "--tf-back-accent": color,
        "--tf-back-accent-soft": `${color}38`,
        "--tf-back-accent-glow": `${color}66`,
      }}>
      <div className="tf-back-vignette" aria-hidden="true" />
      <div className="tf-back-pattern" aria-hidden="true" />
      <div className="tf-back-starfield" aria-hidden="true" />
      <div className="tf-back-inner-border" aria-hidden="true" />
      <div className="tf-back-inner-border tf-back-inner-border-soft" aria-hidden="true" />
      <div className="tf-back-filigree tf-back-filigree-left" aria-hidden="true">❧</div>
      <div className="tf-back-filigree tf-back-filigree-right" aria-hidden="true">❧</div>
      <div className="tf-back-corner tf-back-corner-tl" aria-hidden="true">✦</div>
      <div className="tf-back-corner tf-back-corner-tr" aria-hidden="true">✦</div>
      <div className="tf-back-corner tf-back-corner-bl" aria-hidden="true">✦</div>
      <div className="tf-back-corner tf-back-corner-br" aria-hidden="true">✦</div>
      {style === "runic" && (
        <div className="tf-back-rune" aria-hidden="true">ᛟ</div>
      )}
      <div className="relative z-10 flex min-h-full w-full flex-col items-center justify-center text-center">
        <div className="tf-back-crest" style={{ borderColor: color, boxShadow: `0 0 0 5px ${color}16, 0 0 34px ${color}55` }}>
          <div className="tf-back-crest-ring" aria-hidden="true" />
          <div className="tf-back-crest-orbit" aria-hidden="true"><span>✦</span><span>✦</span><span>✦</span><span>✦</span></div>
          <div className="tf-back-crest-core">
            <Emblem className="w-10 h-10" strokeWidth={1.5} style={{ color }} />
          </div>
          <span className="tf-back-crest-mark tf-back-crest-mark-top" aria-hidden="true">✦</span>
          <span className="tf-back-crest-mark tf-back-crest-mark-bottom" aria-hidden="true">✦</span>
        </div>
        <div className={`tf-back-wordmark ${exportMode ? "tf-back-wordmark-export" : ""}`}>
          <span>TOME</span><i aria-hidden="true">·</i><span>FORGE</span>
        </div>
        {back.motto && (
          <div className="tf-back-motto">
            <span aria-hidden="true">“</span>
            <p>{back.motto}</p>
            <span aria-hidden="true">”</span>
          </div>
        )}
        <div className="tf-back-rule" aria-hidden="true"><span>◆</span><i /><span>◆</span></div>
      </div>
    </div>
  );
});
CardBack.displayName = "CardBack";
