import { QUICK_FIELDS, attrLabel, typeLabel, DEFAULT_APPEARANCE, FRAME_STYLES } from "@/lib/cardTypes";

const waitForImages = async (element) => {
  const images = Array.from(element?.querySelectorAll("img") || []);
  await Promise.all(images.map((img) => {
    if (img.complete) return Promise.resolve();
    return new Promise((resolve) => {
      img.addEventListener("load", resolve, { once: true });
      img.addEventListener("error", resolve, { once: true });
    });
  }));
};

const ABILITIES = ["for", "des", "cos", "int", "sag", "car"];

const getExportFrameColors = (card, appearance = {}) => {
  if (appearance.frame_custom_color_enabled) {
    const color = appearance.frame_custom_color || "#d4af37";
    return [color, "#ffffff", color];
  }
  return FRAME_STYLES.find((style) => style.id === card.frame)?.colors || FRAME_STYLES[0].colors;
};

// Keep these dimensions independent of CSS so PNG, the single-card PDF, and
// every physical size on the A4 sheet all originate from the same safe area.
export const CARD_CANVAS_SIZE = Object.freeze({ width: 340, height: 476, scale: 3 });

export const SINGLE_CARD_A4_BOUNDS = Object.freeze({
  x: 73.25,
  y: 104.05,
  w: 63.5,
  h: 88.9,
});
export const getCardExportLayout = (card) => {
  const attrs = card.attributes || {};
  const has = (key) => {
    const value = attrs[key];
    return (typeof value === "string" || typeof value === "number") && String(value).trim() !== "";
  };
  const abilities = (card.type === "monster" || card.type === "character")
    ? ABILITIES.filter(has).map((key) => [key.toUpperCase(), String(attrs[key])])
    : [];
  let keys = (QUICK_FIELDS[card.type] || []).filter(has);
  if (!keys.length) {
    keys = Object.keys(attrs).filter((key) => has(key) && !ABILITIES.includes(key));
  }
  return {
    abilities,
    fields: keys.slice(0, 6).map((key) => [attrLabel(key), String(attrs[key])]),
  };
};

const drawFittedText = (ctx, text, x, y, maxWidth, size, family, weight = "400") => {
  let currentSize = size;
  const minSize = Math.min(8, size);
  do {
    ctx.font = `${weight} ${currentSize}px ${family}`;
    currentSize -= 0.5;
  } while (currentSize > minSize && ctx.measureText(text).width > maxWidth);
  ctx.font = `${weight} ${Math.max(minSize, currentSize)}px ${family}`;
  ctx.fillText(text, x, y, maxWidth);
};

const drawCategorySymbol = (ctx, type, cx, cy) => {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.strokeStyle = "#f8d764";
  ctx.fillStyle = "#f8d764";
  ctx.lineWidth = 1.5;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  if (type === "spell" || type === "custom") {
    ctx.beginPath();
    for (let i = 0; i < 16; i += 1) {
      const angle = -Math.PI / 2 + (Math.PI * i) / 8;
      const radius = i % 2 === 0 ? 8 : 3.2;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    type === "spell" ? ctx.fill() : ctx.stroke();
  } else if (type === "weapon") {
    ctx.beginPath();
    ctx.moveTo(-6, 7);
    ctx.lineTo(6, -7);
    ctx.moveTo(3.5, -7);
    ctx.lineTo(7, -7);
    ctx.lineTo(7, -3.5);
    ctx.moveTo(-7, 3);
    ctx.lineTo(-3, 7);
    ctx.stroke();
  } else if (type === "armor") {
    ctx.beginPath();
    ctx.moveTo(0, -8);
    ctx.lineTo(7, -5);
    ctx.lineTo(6, 2);
    ctx.quadraticCurveTo(4, 7, 0, 9);
    ctx.quadraticCurveTo(-4, 7, -6, 2);
    ctx.lineTo(-7, -5);
    ctx.closePath();
    ctx.stroke();
  } else if (type === "item") {
    ctx.strokeRect(-7, -5, 14, 12);
    ctx.beginPath();
    ctx.moveTo(-7, -1);
    ctx.lineTo(7, -1);
    ctx.moveTo(0, -5);
    ctx.lineTo(0, 7);
    ctx.stroke();
  } else if (type === "class") {
    ctx.beginPath();
    ctx.moveTo(0, -8);
    ctx.lineTo(7, -5);
    ctx.lineTo(6, 2);
    ctx.quadraticCurveTo(4, 7, 0, 9);
    ctx.quadraticCurveTo(-4, 7, -6, 2);
    ctx.lineTo(-7, -5);
    ctx.closePath();
    ctx.stroke();
  } else if (type === "race") {
    ctx.beginPath();
    ctx.arc(0, -4, 3, 0, Math.PI * 2);
    ctx.arc(-5, -1, 2.2, 0, Math.PI * 2);
    ctx.arc(5, -1, 2.2, 0, Math.PI * 2);
    ctx.moveTo(-7, 7);
    ctx.quadraticCurveTo(0, 0, 7, 7);
    ctx.stroke();
  } else if (type === "feat") {
    ctx.beginPath();
    ctx.arc(0, -2, 6, 0, Math.PI * 2);
    ctx.moveTo(-4, 3);
    ctx.lineTo(-5, 9);
    ctx.lineTo(0, 6);
    ctx.lineTo(5, 9);
    ctx.lineTo(4, 3);
    ctx.stroke();
  } else if (type === "monster") {
    ctx.beginPath();
    ctx.arc(0, -1, 7, Math.PI, 0);
    ctx.lineTo(6, 5);
    ctx.lineTo(3, 8);
    ctx.lineTo(-3, 8);
    ctx.lineTo(-6, 5);
    ctx.closePath();
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(-2.5, 0, 1.2, 0, Math.PI * 2);
    ctx.arc(2.5, 0, 1.2, 0, Math.PI * 2);
    ctx.fill();
  } else {
    ctx.beginPath();
    ctx.arc(0, -4, 3.5, 0, Math.PI * 2);
    ctx.moveTo(-7, 8);
    ctx.quadraticCurveTo(-6, 1, 0, 1);
    ctx.quadraticCurveTo(6, 1, 7, 8);
    ctx.stroke();
  }
  ctx.restore();
};

const colorToRgb = (hex) => {
  const match = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex || "");
  return match
    ? [parseInt(match[1], 16), parseInt(match[2], 16), parseInt(match[3], 16)]
    : [127, 29, 29];
};

const drawWrappedText = (ctx, text, x, y, maxWidth, lineHeight, maxLines = 2) => {
  const words = String(text || "").trim().split(/\s+/).filter(Boolean);
  const lines = [];
  let line = "";

  const pushWord = (word) => {
    let segment = "";
    Array.from(word).forEach((character) => {
      const next = segment + character;
      if (segment && ctx.measureText(next).width > maxWidth) {
        lines.push(segment);
        segment = character;
      } else {
        segment = next;
      }
    });
    if (segment) line = segment;
  };

  words.forEach((word) => {
    const next = line ? `${line} ${word}` : word;
    if (line && ctx.measureText(next).width > maxWidth) {
      lines.push(line);
      if (ctx.measureText(word).width > maxWidth) pushWord(word);
      else line = word;
    } else {
      if (!line && ctx.measureText(word).width > maxWidth) pushWord(word);
      else line = next;
    }
  });
  if (line) lines.push(line);
  lines.slice(0, maxLines).forEach((value, index) => ctx.fillText(value, x, y + index * lineHeight, maxWidth));
};

const drawBackEmblem = (ctx, emblem, cx, cy, accent) => {
  const glyphs = {
    flame: "♨",
    skull: "☠",
    dragon: "♜",
    sword: "⚔",
    moon: "☾",
    eye: "◉",
    shield: "⬡",
    star: "✦",
  };
  ctx.save();
  ctx.fillStyle = accent;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = "400 50px Georgia, 'Times New Roman', serif";
  ctx.shadowColor = `${accent}88`;
  ctx.shadowBlur = 12;
  ctx.fillText(glyphs[emblem] || glyphs.flame, cx, cy + 1);
  ctx.restore();
};

// Dedicated raster renderer for A4 sheets. It mirrors the card composition
// but never asks the browser to screenshot a flex/overflow DOM tree.
export async function renderCardCanvas(element, card) {
  if (!element) throw new Error("Card render unavailable");
  await waitForImages(element);
  if (document.fonts?.ready) await document.fonts.ready;

  const { scale, width, height } = CARD_CANVAS_SIZE;
  const canvas = document.createElement("canvas");
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);
  const appearance = { ...DEFAULT_APPEARANCE, ...(card.appearance || {}) };
  if (appearance.front_background_gradient) {
    const frontBackground = ctx.createLinearGradient(0, 0, width, height);
    frontBackground.addColorStop(0, appearance.front_background_start || "#151311");
    frontBackground.addColorStop(1, appearance.front_background_end || "#151311");
    ctx.fillStyle = frontBackground;
  } else {
    ctx.fillStyle = appearance.front_background_start || "#151311";
  }
  ctx.fillRect(0, 0, width, height);

  const frameColors = getExportFrameColors(card, appearance);
  const border = ctx.createLinearGradient(0, 0, width, height);
  frameColors.forEach((color, index) => border.addColorStop(index / (frameColors.length - 1), color));
  ctx.strokeStyle = border;
  ctx.lineWidth = 3;
  ctx.strokeRect(1.5, 1.5, width - 3, height - 3);
  ctx.strokeStyle = "rgba(232, 196, 96, 0.42)";
  ctx.lineWidth = 1;
  ctx.strokeRect(7.5, 7.5, width - 15, height - 15);
  [[12, 12], [328, 12], [12, 464], [328, 464]].forEach(([x, y]) => {
    ctx.beginPath();
    ctx.arc(x, y, 2, 0, Math.PI * 2);
    ctx.fillStyle = "#f8d764";
    ctx.fill();
  });

  const gold = "#f8d764";
  const light = "#f5f1df";
  const titleColors = appearance.title_custom_color_enabled
    ? [appearance.title_custom_color || gold, appearance.title_custom_color || gold, appearance.title_custom_color || gold]
    : ({
    gold: ["#fffbd1", "#f8d764", "#c98b18"],
    silver: ["#ffffff", "#cbd5e1", "#64748b"],
    rainbow: ["#fb7185", "#facc15", "#34d399", "#60a5fa", "#c084fc"],
    crimson: ["#ffe4e6", "#fb7185", "#881337"],
    azure: ["#e0f2fe", "#38bdf8", "#1e3a8a"],
    violet: ["#f3e8ff", "#c084fc", "#581c87"],
    emerald: ["#d1fae5", "#34d399", "#064e3b"],
    copper: ["#ffedd5", "#fb923c", "#7c2d12"],
    rose: ["#fff1f2", "#fb7185", "#9f1239"],
    arctic: ["#ecfeff", "#67e8f9", "#0e7490"],
    onyx: ["#f8fafc", "#94a3b8", "#0f172a"],
    amber: ["#fffbeb", "#fbbf24", "#92400e"],
    ruby: ["#fee2e2", "#ef4444", "#7f1d1d"],
  }[appearance.title_effect] || ["#fffbd1", "#f8d764", "#c98b18"]);
  const titleGradient = ctx.createLinearGradient(12, 12, 238, 36);
  titleColors.forEach((color, index) => titleGradient.addColorStop(index / (titleColors.length - 1), color));
  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = titleGradient;
  if (appearance.title_shadow !== false) {
    ctx.shadowColor = "rgba(0, 0, 0, 0.95)";
    ctx.shadowBlur = 5;
    ctx.shadowOffsetY = 3;
  }
  drawFittedText(ctx, String(card.name || "Senza nome"), 12, 32, 215, 18, "'Cormorant Garamond', Georgia, serif", "700");
  ctx.shadowColor = "transparent";
  ctx.shadowBlur = 0;
  ctx.shadowOffsetY = 0;
  ctx.font = "600 10px 'Cinzel', Georgia, serif";
  ctx.textAlign = "right";
  ctx.fillStyle = gold;
  drawFittedText(ctx, typeLabel(card.type, card.custom_type).toUpperCase(), 290, 29, 52, 8, "'Cinzel', Georgia, serif", "600");
  ctx.textAlign = "left";
  ctx.fillStyle = "#0c0a09";
  ctx.beginPath();
  ctx.arc(312, 25, 13, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = gold;
  ctx.lineWidth = 1;
  ctx.stroke();
  drawCategorySymbol(ctx, card.type, 312, 25);

  const divider = ctx.createLinearGradient(12, 0, 328, 0);
  divider.addColorStop(0, "transparent");
  divider.addColorStop(0.5, "#d4af37");
  divider.addColorStop(1, "transparent");
  ctx.fillStyle = divider;
  ctx.fillRect(12, 42, 316, 2);

  const artwork = element.querySelector("img");
  const artX = 12, artY = 53, artW = 316, artH = 234;
  ctx.fillStyle = "#090f10";
  ctx.fillRect(artX, artY, artW, artH);
  try {
    if (artwork?.complete && artwork.naturalWidth) ctx.drawImage(artwork, artX, artY, artW, artH);
  } catch {
    // Keep the dark artwork panel if a cross-origin image cannot be drawn.
  }
  ctx.strokeStyle = "#9a7d2e";
  ctx.lineWidth = 1;
  ctx.strokeRect(artX, artY, artW, artH);

  const { abilities, fields } = getCardExportLayout(card);
  const statY = 299;
  if (abilities.length) {
    const abilityGap = 3;
    const abilityW = (316 - abilityGap * 5) / 6;
    abilities.forEach(([label, value], index) => {
      const cellX = 12 + index * (abilityW + abilityGap);
      ctx.strokeStyle = "#b4933c";
      ctx.strokeRect(cellX, statY, abilityW, 28);
      ctx.textAlign = "center";
      ctx.fillStyle = gold;
      ctx.font = "700 7px 'Cinzel', Georgia, serif";
      drawFittedText(ctx, label, cellX + abilityW / 2, statY + 10, abilityW - 5, 7, "'Cinzel', Georgia, serif", "700");
      ctx.fillStyle = light;
      drawFittedText(ctx, value, cellX + abilityW / 2, statY + 23, abilityW - 5, 11, "'Spectral', Georgia, serif", "600");
    });
  }

  const fieldStartY = abilities.length ? 334 : statY;
  const cellW = 154;
  const cellH = 22;
  fields.forEach(([label, value], index) => {
    const col = index % 2;
    const row = Math.floor(index / 2);
    const cellX = 12 + col * 162;
    const cellY = fieldStartY + row * 26;
    ctx.strokeStyle = "#b4933c";
    ctx.strokeRect(cellX, cellY, cellW, cellH);
    ctx.textAlign = "left";
    ctx.fillStyle = gold;
    drawFittedText(ctx, label.toUpperCase(), cellX + 6, cellY + 9, cellW - 12, 7, "'Cinzel', Georgia, serif", "700");
    ctx.fillStyle = light;
    drawFittedText(ctx, value, cellX + 6, cellY + 19, cellW - 12, 10, "'Spectral', Georgia, serif");
  });
  ctx.textAlign = "left";

  const description = String(card.description || "").trim();
  if (description) {
    const rows = Math.ceil(fields.length / 2);
    const descriptionY = fields.length
      ? fieldStartY + rows * 26 + 5
      : abilities.length ? 334 : 303;
    // The footer starts at 452. Reserve an 8px gutter so six statistics and
    // a two-line description can never paint over the footer or be clipped.
    const descriptionHeight = Math.min(39, 444 - descriptionY);
    const descriptionLines = descriptionHeight >= 26 ? 2 : 1;
    const descriptionOpacity = Math.max(0.3, Math.min(0.9, Number(appearance.description_opacity) || 0.64));
    if (descriptionHeight >= 15) {
      const [panelRed, panelGreen, panelBlue] = colorToRgb(appearance.text_panel_color || "#05080a");
      ctx.fillStyle = `rgba(${panelRed}, ${panelGreen}, ${panelBlue}, ${descriptionOpacity})`;
      ctx.fillRect(12, descriptionY, 250, descriptionHeight);
      ctx.strokeStyle = "rgba(201, 160, 58, 0.45)";
      ctx.strokeRect(12.5, descriptionY + 0.5, 249, descriptionHeight - 1);
      ctx.fillStyle = appearance.text_color || light;
      ctx.font = "italic 10px 'Spectral', Georgia, serif";
      drawWrappedText(ctx, description, 19, descriptionY + 13, 232, 12, descriptionLines);
    }
  }

  ctx.fillStyle = light;
  ctx.font = "600 8px 'Cinzel', Georgia, serif";
  ctx.fillText("DETTAGLI COMPLETI", 12, 452);
  ctx.font = "700 12px Arial, sans-serif";
  ctx.fillText(">", 12, 466);

  const qr = element.querySelector("canvas");
  if (qr) {
    ctx.fillStyle = "#fff";
    ctx.fillRect(274, 405, 54, 54);
    ctx.drawImage(qr, 278, 409, 46, 46);
  }
  return canvas;
}

// Dedicated back renderer for duplex sheets and card PDFs. Keeping the back
// independent from DOM capture prevents motto and wordmark clipping on iOS.
export async function renderCardBackCanvas(card) {
  if (document.fonts?.ready) await document.fonts.ready;

  const { scale, width, height } = CARD_CANVAS_SIZE;
  const canvas = document.createElement("canvas");
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);

  const back = card.back || {};
  const style = back.style || "classic";
  const accent = back.color || "#7f1d1d";
  const [r, g, b] = colorToRgb(accent);
  const appearance = { ...DEFAULT_APPEARANCE, ...(card.appearance || {}) };
  const frameColors = getExportFrameColors(card, appearance);

  const background = ctx.createLinearGradient(0, 0, width, height);
  background.addColorStop(0, style === "arcane" ? "#10192a" : "#241a18");
  background.addColorStop(0.5, "#09090c");
  background.addColorStop(1, style === "damask" ? "#211421" : "#1b1415");
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, width, height);

  const aura = ctx.createRadialGradient(width / 2, 210, 15, width / 2, 210, style === "runic" ? 190 : 150);
  aura.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${style === "arcane" ? 0.52 : 0.38})`);
  aura.addColorStop(1, "rgba(0, 0, 0, 0)");
  ctx.fillStyle = aura;
  ctx.fillRect(0, 0, width, height);

  const border = ctx.createLinearGradient(0, 0, width, height);
  frameColors.forEach((color, index) => border.addColorStop(index / (frameColors.length - 1), color));
  ctx.strokeStyle = border;
  ctx.lineWidth = 3;
  ctx.strokeRect(1.5, 1.5, width - 3, height - 3);
  ctx.strokeStyle = "rgba(232, 196, 96, 0.48)";
  ctx.lineWidth = 1;
  ctx.strokeRect(9.5, 9.5, width - 19, height - 19);
  ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.62)`;
  ctx.strokeRect(15.5, 15.5, width - 31, height - 31);

  ctx.save();
  ctx.translate(width / 2, 210);
  if (style === "arcane") {
    ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.36)`;
    for (let i = 0; i < 16; i += 1) {
      ctx.rotate(Math.PI / 8);
      ctx.beginPath();
      ctx.moveTo(72, 0);
      ctx.lineTo(132, 0);
      ctx.stroke();
    }
  } else if (style === "runic") {
    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.7)`;
    ctx.font = "400 15px Georgia, serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (let i = 0; i < 12; i += 1) {
      const angle = (Math.PI * 2 * i) / 12;
      ctx.fillText(i % 2 ? "ᚱ" : "ᛟ", Math.cos(angle) * 116, Math.sin(angle) * 116);
    }
  } else if (style === "damask") {
    ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.42)`;
    ctx.lineWidth = 1.2;
    for (let i = 0; i < 4; i += 1) {
      ctx.rotate(Math.PI / 2);
      ctx.beginPath();
      ctx.moveTo(0, -62);
      ctx.bezierCurveTo(34, -82, 78, -70, 102, -112);
      ctx.bezierCurveTo(83, -75, 78, -33, 46, -25);
      ctx.stroke();
    }
  }
  ctx.restore();

  [[19, 19, 1, 1], [321, 19, -1, 1], [19, 457, 1, -1], [321, 457, -1, -1]].forEach(([x, y, sx, sy]) => {
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(sx, sy);
    ctx.strokeStyle = "#d7b652";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, 18);
    ctx.lineTo(0, 0);
    ctx.lineTo(18, 0);
    ctx.moveTo(4, 14);
    ctx.quadraticCurveTo(4, 4, 14, 4);
    ctx.stroke();
    ctx.restore();
  });

  ctx.fillStyle = "rgba(232, 196, 96, 0.58)";
  [[53, 91], [286, 98], [75, 342], [269, 339], [43, 391], [297, 395]].forEach(([x, y]) => {
    ctx.fillRect(x, y, 1.5, 1.5);
  });
  ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.46)`;
  ctx.lineWidth = 1;
  [-1, 1].forEach((side) => {
    ctx.save();
    ctx.translate(width / 2 + side * 93, 210);
    ctx.scale(side, 1);
    ctx.beginPath();
    ctx.moveTo(0, -54);
    ctx.bezierCurveTo(20, -44, 27, -25, 15, -6);
    ctx.bezierCurveTo(31, 8, 28, 30, 0, 51);
    ctx.stroke();
    ctx.restore();
  });

  ctx.strokeStyle = accent;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(width / 2, 210, 68, 0, Math.PI * 2);
  ctx.stroke();
  ctx.strokeStyle = "rgba(232, 196, 96, 0.62)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(width / 2, 210, 57, 0, Math.PI * 2);
  ctx.stroke();
  ctx.fillStyle = "rgba(232, 196, 96, 0.72)";
  ctx.font = "400 8px Georgia, serif";
  for (let i = 0; i < 8; i += 1) {
    const angle = (Math.PI * 2 * i) / 8;
    ctx.fillText("✦", width / 2 + Math.cos(angle) * 63, 213 + Math.sin(angle) * 63);
  }
  ctx.fillStyle = "rgba(5, 6, 8, 0.76)";
  ctx.beginPath();
  ctx.arc(width / 2, 210, 47, 0, Math.PI * 2);
  ctx.fill();
  drawBackEmblem(ctx, back.emblem, width / 2, 210, accent);

  const wordmark = ctx.createLinearGradient(80, 282, 260, 318);
  wordmark.addColorStop(0, "#9a6c19");
  wordmark.addColorStop(0.48, "#fff0a0");
  wordmark.addColorStop(1, "#9a6c19");
  ctx.fillStyle = wordmark;
  ctx.font = "700 30px 'Cinzel Decorative', Georgia, serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "alphabetic";
  ctx.fillText("TOME · FORGE", width / 2, 315);

  if (String(back.motto || "").trim()) {
    ctx.strokeStyle = "rgba(216, 186, 97, 0.42)";
    ctx.beginPath();
    ctx.moveTo(94, 365);
    ctx.lineTo(246, 365);
    ctx.stroke();
    ctx.fillStyle = "#f2ead3";
    ctx.font = "italic 12px 'Spectral', Georgia, serif";
    drawWrappedText(ctx, `“${back.motto}”`, width / 2, 388, 230, 17, 2);
  }

  ctx.fillStyle = "rgba(216, 186, 97, 0.7)";
  ctx.font = "400 9px Georgia, serif";
  ctx.fillText("✦", width / 2, 425);
  return canvas;
}

// These adapters keep the user-facing export routes on the same dedicated
// canvas path as the regression tests, rather than reintroducing DOM capture.
export const createCardPng = (element, card) => renderCardCanvas(element, card);

export async function addSingleCardPdfPages(pdf, element, card) {
  const [front, back] = await Promise.all([
    renderCardCanvas(element, card),
    renderCardBackCanvas(card),
  ]);
  pdf.addImage(front.toDataURL("image/png"), "PNG", 0, 0, 63.5, 88.9);
  pdf.addPage([63.5, 88.9], "portrait");
  pdf.addImage(back.toDataURL("image/png"), "PNG", 0, 0, 63.5, 88.9);
  return { front, back };
}

export async function addPrintSheetCard(pdf, element, card, bounds, back = false) {
  const canvas = back
    ? await renderCardBackCanvas(card)
    : await renderCardCanvas(element, card);
  pdf.addImage(canvas.toDataURL("image/png"), "PNG", bounds.x, bounds.y, bounds.w, bounds.h);
  return canvas;
}

export async function addSingleCardA4PdfPages(pdf, element, card) {
  const front = await addPrintSheetCard(pdf, element, card, SINGLE_CARD_A4_BOUNDS);
  pdf.addPage();
  const back = await addPrintSheetCard(pdf, null, card, SINGLE_CARD_A4_BOUNDS, true);
  return { front, back };
}
