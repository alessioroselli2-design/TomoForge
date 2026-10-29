import { buildFrontBlueprint } from "@/lib/cardFrontBlueprint";
import { getApprovedBack } from "@/lib/cardBacks";

const ABILITIES = ["for", "des", "cos", "int", "sag", "car"];

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

// A single data blueprint drives both the interactive card and every physical export.
export const CARD_CANVAS_SIZE = Object.freeze({ width: 340, height: 476, scale: 3 });

export const SINGLE_CARD_A4_BOUNDS = Object.freeze({
  x: 73.25, y: 104.05, w: 63.5, h: 88.9,
});

export const getCardExportLayout = (card) => {
  const blueprint = buildFrontBlueprint(card);
  return {
    abilities: blueprint.abilities.map(({ label, value }) => [label, value]),
    fields: blueprint.highlights.map(({ label, value }) => [label, value]),
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



const wrapTextLines = (ctx, text, maxWidth) => {
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
  return lines;
};

const drawWrappedText = (ctx, text, x, y, maxWidth, lineHeight, maxLines = 2) => {
  wrapTextLines(ctx, text, maxWidth)
    .slice(0, maxLines)
    .forEach((value, index) => ctx.fillText(value, x, y + index * lineHeight, maxWidth));
};

// The v2 renderer uses the same category blueprint as the React preview;
// changing the saved card's legacy appearance no longer affects either output.
export async function renderCardCanvas(element, card) {
  if (!element) throw new Error("Card render unavailable");
  await waitForImages(element);
  if (document.fonts?.ready) await document.fonts.ready;
  const data = buildFrontBlueprint(card);
  const { scale, width, height } = CARD_CANVAS_SIZE;
  const canvas = document.createElement("canvas");
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);

  const background = ctx.createLinearGradient(0, 0, width, height);
  background.addColorStop(0, "#101b2f");
  background.addColorStop(0.55, "#10121f");
  background.addColorStop(1, "#1e192a");
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, width, height);

  // Engraved frame, shared across all categories, with a type-specific accent.
  const metal = ctx.createLinearGradient(0, 0, width, height);
  metal.addColorStop(0, "#e8ce8c");
  metal.addColorStop(0.5, "#9f733e");
  metal.addColorStop(1, "#e8ce8c");
  ctx.strokeStyle = metal;
  ctx.lineWidth = 3;
  ctx.strokeRect(1.5, 1.5, width - 3, height - 3);
  ctx.strokeStyle = "rgba(235,195,116,.55)";
  ctx.lineWidth = 1;
  ctx.strokeRect(9, 9, width - 18, height - 18);

  const gold = "#f3d59b";
  const ink = "#f9eed8";
  ctx.textAlign = "left";
  ctx.fillStyle = data.accent;
  drawFittedText(ctx, data.heading + "  ✦  TOMOFORGE", 18, 25, 240, 9, "'Cinzel',Georgia,serif", "700");
  ctx.fillStyle = gold;
  drawFittedText(ctx, data.name, 18, 48, 252, 20, "'Cormorant Garamond',Georgia,serif", "700");
  ctx.fillStyle = "#b7c6dd";
  drawFittedText(ctx, data.subtitle, 18, 65, 258, 10, "'Spectral',Georgia,serif");

  ctx.beginPath();
  ctx.arc(303, 43, 20, 0, 2 * Math.PI);
  ctx.fillStyle = "#1b2033";
  ctx.fill();
  ctx.strokeStyle = "#dbbc7c";
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = ink;
  ctx.textAlign = "center";
  drawFittedText(ctx, data.crest, 303, 47, 32, 12, "'Cinzel',Georgia,serif", "700");
  ctx.textAlign = "left";

  const artX = 16, artY = 82, artW = 308, artH = data.hasAbilities ? 191 : 220;
  ctx.fillStyle = "#090f1c";
  ctx.fillRect(artX, artY, artW, artH);
  let artworkDrawn = false;
  const artwork = element.querySelector("img");
  try {
    if (artwork?.complete && artwork.naturalWidth > 0) {
      // Cover/crop rather than stretch: print and mobile preview preserve aspect ratio.
      const imageWidth = artwork.naturalWidth;
      const imageHeight = artwork.naturalHeight || imageWidth;
      const ratio = Math.max(artW / imageWidth, artH / imageHeight);
      const cropW = artW / ratio;
      const cropH = artH / ratio;
      ctx.drawImage(artwork,
        (imageWidth - cropW) / 2, (imageHeight - cropH) / 2, cropW, cropH,
        artX, artY, artW, artH);
      artworkDrawn = true;
    }
  } catch {
    // Broken or CORS-restricted artwork never breaks a PDF. Keep dark art panel.
  }
  ctx.strokeStyle = "#b99b5d";
  ctx.lineWidth = 1;
  ctx.strokeRect(artX, artY, artW, artH);
  if (data.dice) {
    ctx.fillStyle = "rgba(10,20,34,.94)";
    ctx.fillRect(artX + artW - 91, artY + artH - 29, 85, 23);
    ctx.strokeStyle = "#e8c980";
    ctx.strokeRect(artX + artW - 91, artY + artH - 29, 85, 23);
    ctx.fillStyle = ink;
    ctx.textAlign = "center";
    drawFittedText(ctx, data.dice, artX + artW - 49, artY + artH - 13, 78, 12, "'Cinzel',Georgia,serif", "700");
    ctx.textAlign = "left";
  }

  const statsY = data.hasAbilities ? 282 : 309;
  const stats = data.highlights;
  if (stats.length) {
    const gap = 4, cellWidth = (308 - gap * (stats.length - 1)) / stats.length;
    stats.forEach(({ label, value }, index) => {
      const x = 16 + index * (cellWidth + gap);
      ctx.fillStyle = "#17243a";
      ctx.fillRect(x, statsY, cellWidth, 40);
      ctx.strokeStyle = "rgba(227,186,107,.7)";
      ctx.strokeRect(x, statsY, cellWidth, 40);
      ctx.fillStyle = "#d8b879";
      ctx.textAlign = "center";
      drawFittedText(ctx, label.toUpperCase(), x + cellWidth / 2, statsY + 14, cellWidth - 8, 8, "'Cinzel',Georgia,serif", "700");
      ctx.fillStyle = ink;
      drawFittedText(ctx, value, x + cellWidth / 2, statsY + 31, cellWidth - 8, 13, "'Spectral',Georgia,serif", "700");
    });
    ctx.textAlign = "left";
  } else {
    ctx.fillStyle = "#aab4c7";
    ctx.font = "9px Georgia,serif";
    ctx.fillText("DATI IN ATTESA DI COMPILAZIONE", 21, statsY + 25);
  }

  if (data.hasAbilities) {
    const y = 329, gap = 3, cellWidth = (308 - gap * 5) / 6;
    data.abilities.forEach(({ label, value }, index) => {
      const x = 16 + index * (cellWidth + gap);
      ctx.fillStyle = "#101927";
      ctx.fillRect(x, y, cellWidth, 37);
      ctx.strokeStyle = "#8b7757";
      ctx.strokeRect(x, y, cellWidth, 37);
      ctx.textAlign = "center";
      ctx.fillStyle = "#dfc18d";
      drawFittedText(ctx, label, x + cellWidth / 2, y + 13, cellWidth - 5, 8, "'Cinzel',Georgia,serif", "700");
      ctx.fillStyle = ink;
      drawFittedText(ctx, value, x + cellWidth / 2, y + 29, cellWidth - 5, 12, "'Spectral',Georgia,serif", "700");
    });
    ctx.textAlign = "left";
  }

  const notesY = data.hasAbilities ? 375 : 356;
  const notesH = data.hasAbilities ? 65 : 84;
  ctx.fillStyle = "#0d1422";
  ctx.fillRect(16, notesY, 308, notesH);
  ctx.strokeStyle = "#b1955e";
  ctx.strokeRect(16, notesY, 308, notesH);
  let textY = notesY + 15;
  data.details.slice(0, data.hasAbilities ? 2 : 3).forEach(({ label, value }) => {
    ctx.fillStyle = "#dfbb78";
    ctx.font = "700 8px 'Cinzel',Georgia,serif";
    const detail = label.toUpperCase() + ": " + value;
    drawFittedText(ctx, detail, 23, textY, 292, 9, "'Spectral',Georgia,serif", "600");
    textY += 13;
  });
  const desc = data.description || "Le informazioni della carta appariranno qui dopo la selezione di un record.";
  ctx.font = "italic 10px 'Spectral',Georgia,serif";
  ctx.fillStyle = "#f4e6d0";
  const maxLines = Math.max(1, Math.floor((notesY + notesH - textY - 4) / 12));
  drawWrappedText(ctx, desc, 23, textY + 1, 292, 12, Math.min(3, maxLines));

  ctx.fillStyle = "#d7b980";
  ctx.font = "700 8px 'Cinzel',Georgia,serif";
  ctx.fillText("✦ TOMOFORGE", 18, 457);
  ctx.textAlign = "right";
  ctx.fillText(data.heading, 323, 457);
  ctx.textAlign = "left";
  canvas.artworkDrawn = artworkDrawn;
  return canvas;
}

// Dedicated back renderer for duplex sheets and card PDFs. Keeping the back
// independent from DOM capture prevents motto and wordmark clipping on iOS.
export async function renderCardBackCanvas(card) {
  // The same official artwork is used in preview, PNG, individual PDF and A4.
  // Load it explicitly to avoid a blank canvas on Safari/iPhone.
  const { scale, width, height } = CARD_CANVAS_SIZE;
  const canvas = document.createElement("canvas");
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext("2d");
  const art = getApprovedBack(card);
  const image = new Image();
  await new Promise((resolve, reject) => {
    image.onload = resolve;
    image.onerror = () => reject(new Error(`Dorso ufficiale non disponibile: ${art.src}`));
    image.src = art.src;
    if (image.complete && image.naturalWidth > 0) resolve();
  });
  // Do not stretch any original frame, oval, wordmark or book. A back that
  // already has the print ratio fills the entire canvas; otherwise the entire
  // drawing is letterboxed, never cropped.
  const naturalWidth = image.naturalWidth || canvas.width;
  const naturalHeight = image.naturalHeight || naturalWidth * (canvas.height / canvas.width);
  const fit = Math.min(canvas.width / naturalWidth, canvas.height / naturalHeight);
  const drawWidth = Math.min(canvas.width, naturalWidth * fit);
  const drawHeight = Math.min(canvas.height, naturalHeight * fit);
  ctx.fillStyle = "#101019";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(image, (canvas.width - drawWidth) / 2, (canvas.height - drawHeight) / 2, drawWidth, drawHeight);
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

// A character sheet is intentionally a separate fixed-coordinate renderer:
// unlike a trading card it needs the whole A4 surface and must remain stable
// when saved as a browser PDF on desktop or mobile.
export const CHARACTER_SHEET_CANVAS_SIZE = Object.freeze({ width: 794, height: 1123, scale: 2 });

const sheetValue = (value, fallback = "—") => hasSheetValue(value) ? String(value) : fallback;
const hasSheetValue = (value) => value !== undefined && value !== null && String(value).trim() !== "";

const sheetListItems = (value) => {
  if (Array.isArray(value)) return value;
  if (typeof value === "string") return value.split(/\n|,/);
  return [];
};

const sheetTextLines = (items = []) => sheetListItems(items)
  .map((item) => typeof item === "string" ? item.trim() : item?.nome || item?.name || "")
  .filter(Boolean)
  .join(" · ") || "—";

const sheetBox = (ctx, x, y, width, height, label, value, color = "#d4af37") => {
  ctx.strokeStyle = color;
  ctx.lineWidth = 1;
  ctx.strokeRect(x, y, width, height);
  ctx.fillStyle = color;
  ctx.font = "700 9px 'Cinzel', Georgia, serif";
  ctx.fillText(label.toUpperCase(), x + 10, y + 15, width - 20);
  ctx.fillStyle = "#201b15";
  ctx.font = "600 16px 'Spectral', Georgia, serif";
  drawWrappedText(ctx, String(value || "—"), x + 10, y + 35, width - 20, 17, Math.max(1, Math.floor((height - 28) / 17)));
};

const sheetListLines = (ctx, value, width) => {
  ctx.font = "600 16px 'Spectral', Georgia, serif";
  return wrapTextLines(ctx, sheetTextLines(value), width);
};

const drawSheetBoxLines = (ctx, x, y, width, height, label, lines, color = "#d4af37") => {
  ctx.strokeStyle = color;
  ctx.lineWidth = 1;
  ctx.strokeRect(x, y, width, height);
  ctx.fillStyle = color;
  ctx.font = "700 9px 'Cinzel', Georgia, serif";
  ctx.fillText(label.toUpperCase(), x + 10, y + 15, width - 20);
  ctx.fillStyle = "#201b15";
  ctx.font = "600 16px 'Spectral', Georgia, serif";
  const maxLines = Math.max(1, Math.floor((height - 28) / 17));
  lines.slice(0, maxLines).forEach((line, index) => {
    ctx.fillText(line, x + 10, y + 35 + index * 17, width - 20);
  });
};

const createCharacterSheetCanvas = async (card) => {
  if (document.fonts?.ready) await document.fonts.ready;
  const { width, height, scale } = CHARACTER_SHEET_CANVAS_SIZE;
  const canvas = document.createElement("canvas");
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);

  const attrs = card.attributes || {};
  ctx.fillStyle = "#f5edd7";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#5f4720";
  ctx.lineWidth = 3;
  ctx.strokeRect(18, 18, width - 36, height - 36);
  ctx.strokeStyle = "#b69347";
  ctx.lineWidth = 1;
  ctx.strokeRect(27, 27, width - 54, height - 54);

  ctx.fillStyle = "#34220e";
  ctx.font = "700 30px 'Cinzel Decorative', Georgia, serif";
  ctx.textAlign = "center";
  ctx.fillText("SCHEDA DEL PERSONAGGIO", width / 2, 70);
  ctx.font = "italic 15px 'Spectral', Georgia, serif";
  ctx.fillStyle = "#765925";
  ctx.fillText("TomeForge · dati regolamentari e scelte dell'avventuriero", width / 2, 94);
  ctx.textAlign = "left";

  sheetBox(ctx, 48, 118, 382, 58, "Nome", sheetValue(card.name));
  sheetBox(ctx, 444, 118, 302, 58, "Livello", sheetValue(attrs.livello));
  sheetBox(ctx, 48, 188, 224, 58, "Razza", sheetValue(attrs.razza));
  sheetBox(ctx, 284, 188, 224, 58, "Classe", sheetValue(attrs.classe));
  sheetBox(ctx, 520, 188, 226, 58, "Sottoclasse", sheetValue(attrs.sottoclasse));

  const abilityY = 268;
  const abilityWidth = 111;
  ABILITIES.forEach((ability, index) => {
    const x = 48 + index * (abilityWidth + 6);
    ctx.fillStyle = "#34220e";
    ctx.fillRect(x, abilityY, abilityWidth, 77);
    ctx.strokeStyle = "#b69347";
    ctx.strokeRect(x, abilityY, abilityWidth, 77);
    ctx.textAlign = "center";
    ctx.fillStyle = "#f5d77a";
    ctx.font = "700 11px 'Cinzel', Georgia, serif";
    ctx.fillText(ability.toUpperCase(), x + abilityWidth / 2, abilityY + 22);
    ctx.fillStyle = "#fff8e7";
    ctx.font = "700 30px 'Spectral', Georgia, serif";
    ctx.fillText(sheetValue(attrs[ability]), x + abilityWidth / 2, abilityY + 57);
  });
  ctx.textAlign = "left";

  sheetBox(ctx, 48, 365, 168, 60, "Classe armatura", sheetValue(attrs.classe_armatura));
  sheetBox(ctx, 228, 365, 168, 60, "Punti ferita", sheetValue(attrs.punti_ferita));
  sheetBox(ctx, 408, 365, 168, 60, "Bonus competenza", sheetValue(attrs.bonus_competenza));
  sheetBox(ctx, 588, 365, 158, 60, "CD incantesimi", sheetValue(attrs.cd_incantesimi));

  sheetBox(ctx, 48, 448, 338, 118, "Competenze", sheetValue(attrs.competenze));
  sheetBox(ctx, 408, 448, 338, 118, "Slot incantesimi", (attrs.slot_incantesimi || [])
    .map((slot) => `L${slot?.livello || "?"}: ${Math.max(0, Number(slot?.totale || 0) - Number(slot?.usati || 0))}/${slot?.totale || 0}`)
    .join(" · ") || "—");
  const listSections = [
    {
      label: "Privilegi",
      value: attrs.privilegi?.length ? attrs.privilegi : attrs.abilita_sottoclasse,
      x: 48,
      y: 586,
      width: 338,
      height: 140,
    },
    {
      label: "Incantesimi",
      value: attrs.incantesimi,
      x: 408,
      y: 586,
      width: 338,
      height: 140,
    },
    {
      label: "Equipaggiamento",
      value: attrs.equipaggiamento,
      x: 48,
      y: 746,
      width: 338,
      height: 140,
    },
  ].map((section) => ({
    ...section,
    lines: sheetListLines(ctx, section.value, section.width - 20),
  }));
  listSections.forEach((section) => {
    drawSheetBoxLines(ctx, section.x, section.y, section.width, section.height, section.label, section.lines);
  });
  sheetBox(ctx, 408, 746, 338, 140, "Note / tratti", sheetValue(attrs.tratti || card.description));

  ctx.strokeStyle = "#b69347";
  ctx.strokeRect(48, 908, 698, 138);
  ctx.fillStyle = "#765925";
  ctx.font = "700 10px 'Cinzel', Georgia, serif";
  ctx.fillText("FONTI NORMATIVE COLLEGATE", 60, 928);
  ctx.fillStyle = "#34220e";
  ctx.font = "14px 'Spectral', Georgia, serif";
  const sources = (card.source_refs || []).map((reference) => `${reference.filename || "Manuale"} · p. ${reference.page || "?"}`).join("  |  ") || "Nessuna fonte normativa collegata.";
  drawWrappedText(ctx, sources, 60, 953, 674, 18, 4);

  ctx.fillStyle = "#765925";
  ctx.font = "italic 11px 'Spectral', Georgia, serif";
  ctx.textAlign = "center";
  ctx.fillText("I valori inseriti o tirati dall'avventuriero non vengono sostituiti dai riferimenti.", width / 2, 1081);
  ctx.textAlign = "left";
  return { canvas, listSections };
};

const drawSheetFrame = (ctx, title, subtitle) => {
  const { width, height } = CHARACTER_SHEET_CANVAS_SIZE;
  ctx.fillStyle = "#f5edd7";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#5f4720";
  ctx.lineWidth = 3;
  ctx.strokeRect(18, 18, width - 36, height - 36);
  ctx.strokeStyle = "#b69347";
  ctx.lineWidth = 1;
  ctx.strokeRect(27, 27, width - 54, height - 54);
  ctx.fillStyle = "#34220e";
  ctx.font = "700 30px 'Cinzel Decorative', Georgia, serif";
  ctx.textAlign = "center";
  ctx.fillText(title, width / 2, 70);
  ctx.font = "italic 15px 'Spectral', Georgia, serif";
  ctx.fillStyle = "#765925";
  ctx.fillText(subtitle, width / 2, 94);
  ctx.textAlign = "left";
};

const createCharacterSheetOverflowCanvas = (card, sections, pageNumber) => {
  const { width, height, scale } = CHARACTER_SHEET_CANVAS_SIZE;
  const canvas = document.createElement("canvas");
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);
  drawSheetFrame(ctx, "CONTENUTI AGGIUNTIVI", `${card.name || "Personaggio"} · pagina ${pageNumber}`);

  const contentX = 48;
  const contentWidth = width - 96;
  const contentBottom = height - 77;
  const lineHeight = 20;
  const sectionHeaderHeight = 30;
  let y = 132;
  ctx.font = "600 16px 'Spectral', Georgia, serif";

  sections.forEach((section) => {
    if (!section.lines.length) return;
    if (y + sectionHeaderHeight + lineHeight > contentBottom) {
      y = contentBottom;
      return;
    }
    ctx.fillStyle = "#765925";
    ctx.font = "700 12px 'Cinzel', Georgia, serif";
    ctx.fillText(section.label.toUpperCase(), contentX, y, contentWidth);
    y += sectionHeaderHeight;
    ctx.fillStyle = "#201b15";
    ctx.font = "600 16px 'Spectral', Georgia, serif";
    section.lines.forEach((line) => {
      if (y + lineHeight > contentBottom) return;
      ctx.fillText(line, contentX + 12, y, contentWidth - 12);
      y += lineHeight;
    });
  });

  ctx.fillStyle = "#765925";
  ctx.font = "italic 11px 'Spectral', Georgia, serif";
  ctx.textAlign = "center";
  ctx.fillText("Continua nella pagina successiva se sono presenti altre voci.", width / 2, height - 42);
  ctx.textAlign = "left";
  return canvas;
};

const paginateSheetOverflow = (sections) => {
  const contentBottom = CHARACTER_SHEET_CANVAS_SIZE.height - 77;
  const lineHeight = 20;
  const sectionHeaderHeight = 30;
  const pages = [];
  let page = [];
  let y = 132;

  const pushPage = () => {
    if (page.length) pages.push(page);
    page = [];
    y = 132;
  };

  sections.forEach((section) => {
    let remaining = section.lines;
    while (remaining.length) {
      if (y + sectionHeaderHeight + lineHeight > contentBottom) pushPage();
      const availableLines = Math.floor((contentBottom - y - sectionHeaderHeight) / lineHeight);
      if (availableLines < 1) {
        pushPage();
        continue;
      }
      const lines = remaining.slice(0, availableLines);
      page.push({ label: section.label, lines });
      y += sectionHeaderHeight + lines.length * lineHeight;
      remaining = remaining.slice(lines.length);
      if (remaining.length && y + sectionHeaderHeight + lineHeight > contentBottom) pushPage();
    }
  });
  pushPage();
  return pages;
};

export async function renderCharacterSheetCanvases(card) {
  if (document.fonts?.ready) await document.fonts.ready;
  const { canvas, listSections } = await createCharacterSheetCanvas(card);
  const overflowSections = listSections.map((section) => {
    const maxLines = Math.max(1, Math.floor((section.height - 28) / 17));
    return { label: section.label, lines: section.lines.slice(maxLines) };
  }).filter((section) => section.lines.length);
  if (!overflowSections.length) return [canvas];

  const overflowPages = paginateSheetOverflow(overflowSections);
  return [
    canvas,
    ...overflowPages.map((sections, index) => createCharacterSheetOverflowCanvas(card, sections, index + 2)),
  ];
}

export async function renderCharacterSheetCanvas(card) {
  const [canvas] = await renderCharacterSheetCanvases(card);
  return canvas;
}

export async function addCharacterSheetPdfPages(pdf, card) {
  const sheets = await renderCharacterSheetCanvases(card);
  sheets.forEach((sheet, index) => {
    if (index) pdf.addPage();
    pdf.addImage(sheet.toDataURL("image/png"), "PNG", 0, 0, 210, 297);
  });
  return sheets;
}

export async function addCharacterSheetPdfPage(pdf, card) {
  const sheet = await renderCharacterSheetCanvas(card);
  pdf.addImage(sheet.toDataURL("image/png"), "PNG", 0, 0, 210, 297);
  return sheet;
}
