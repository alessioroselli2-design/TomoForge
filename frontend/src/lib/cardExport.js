import { buildFrontBlueprint } from "@/lib/cardFrontBlueprint";
import { ORNATE_FRAME_URL, REFERENCE_FRAME_URL, REFERENCE_FRAME_SIMPLE_URL } from "@/lib/ornateFrame";
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

// Premium front v3: the same badge, medallion and parchment information shown
// in CardFront is drawn at physical card size for PNG and both PDF print paths.
const loadFrontEmblem = async (emblem) => {
  if (!emblem) return null;
  const img = new Image();
  try {
    await new Promise((resolve,reject) => {
      img.onload=resolve; img.onerror=reject; img.src=emblem.src;
      if(img.complete && img.naturalWidth>0)resolve();
    });
    return img;
  } catch { return null; }
};
const canvasBox=(ctx,x,y,w,h,fill,stroke="#a3773f")=>{
  ctx.fillStyle=fill;ctx.fillRect(x,y,w,h);
  ctx.strokeStyle=stroke;ctx.lineWidth=1;ctx.strokeRect(x+.5,y+.5,w-1,h-1);
};
export async function renderCardCanvas(element, card) {
  if (!element) throw new Error("Card render unavailable");
  await waitForImages(element);
  if(document.fonts?.ready)await document.fonts.ready;
  const data=buildFrontBlueprint(card);
  const {width,height,scale}=CARD_CANVAS_SIZE;
  const canvas=document.createElement("canvas");
  canvas.width=width*scale;canvas.height=height*scale;
  const ctx=canvas.getContext("2d");
  ctx.scale(scale,scale);
  const background=ctx.createLinearGradient(0,0,width,height);
  background.addColorStop(0,"#2f101a");
  background.addColorStop(.5,data.accent);
  background.addColorStop(1,"#270c18");
  ctx.fillStyle=background;ctx.fillRect(0,0,width,height);
  const gold=ctx.createLinearGradient(0,0,width,height);
  gold.addColorStop(0,"#ffde94");gold.addColorStop(.45,"#b67c32");gold.addColorStop(1,"#ffe5a3");
  ctx.strokeStyle=gold;ctx.lineWidth=5;ctx.strokeRect(3,3,width-6,height-6);
  ctx.lineWidth=1;ctx.strokeRect(10,10,width-20,height-20);
  ctx.fillStyle="#ffe1a3";
  ["✦"].forEach(star => [[9,16],[331,16],[9,467],[331,467]].forEach(([x,y])=>{
    ctx.font="700 13px Georgia,serif";ctx.textAlign="center";ctx.fillText(star,x,y);
  }));

  const BX=15,BW=310;
  // Engraved ivory header.
  const parchment=ctx.createLinearGradient(BX,0,BX+BW,0);
  parchment.addColorStop(0,"#d6a85b");
  parchment.addColorStop(.22,"#fff6d8");
  parchment.addColorStop(.8,"#f7e6bc");
  parchment.addColorStop(1,"#ad763c");
  canvasBox(ctx,BX,16,BW,66,parchment,"#dfb46c");
  ctx.strokeStyle="#925e2e";ctx.strokeRect(BX+3,19,BW-6,60);

  // Approved medal remains an actual image, not a letter-only placeholder.
  const symbol=data.emblem;
  ctx.fillStyle="#0e1425";ctx.beginPath();ctx.arc(48,49,27,0,Math.PI*2);ctx.fill();
  ctx.strokeStyle="#dbb76d";ctx.lineWidth=3;ctx.stroke();
  const emblemImage=await loadFrontEmblem(symbol);
  if(emblemImage && symbol){
    const sx=symbol.col*symbol.cell,sy=symbol.row*symbol.cell;
    ctx.drawImage(emblemImage,sx,sy,symbol.cell,symbol.cell,22,23,52,52);
  } else {
    ctx.fillStyle="#f8d78a";ctx.textAlign="center";ctx.font="700 20px Georgia,serif";ctx.fillText("✦",48,56);
  }
  ctx.fillStyle="#24140d";ctx.textAlign="center";
  drawFittedText(ctx,data.name,182,45,data.badge?176:214,22,"'Cormorant Garamond',Georgia,serif","700");
  ctx.fillStyle="#55381f";
  drawFittedText(ctx,data.subtitle,182,63,data.badge?174:214,10,"'Spectral',Georgia,serif");
  if(data.badge){
    ctx.fillStyle="#0d1934";ctx.beginPath();ctx.arc(297,49,26,0,Math.PI*2);ctx.fill();
    ctx.strokeStyle="#edc478";ctx.lineWidth=3;ctx.stroke();
    ctx.fillStyle="#fce5b2";ctx.textAlign="center";
    ctx.font="700 8px 'Cinzel',Georgia,serif";ctx.fillText(data.badge.top,297,43);
    drawFittedText(ctx,data.badge.value,297,60,40,16,"'Spectral',Georgia,serif","700");
  }
  ctx.textAlign="left";
  const artX=BX,artY=84,artW=BW,artH=data.hasAbilities?166:195;
  canvasBox(ctx,artX,artY,artW,artH,"#100d15","#d5ab64");
  const artwork=element.querySelector("img");
  let artworkDrawn=false;
  try {
    if(artwork?.complete && artwork.naturalWidth>0){
      const iw=artwork.naturalWidth,ih=artwork.naturalHeight||iw;
      const fit=Math.max(artW/iw,artH/ih),sw=artW/fit,sh=artH/fit;
      ctx.drawImage(artwork,(iw-sw)/2,(ih-sh)/2,sw,sh,artX,artY,artW,artH);
      artworkDrawn=true;
    }
  } catch {/* The card remains exportable without a remote image. */}
  ctx.strokeStyle="#d5ab64";ctx.lineWidth=2;ctx.strokeRect(artX,artY,artW,artH);
  // Matching the approved reference: a carved inner line and a gold central jewel.
  ctx.strokeStyle="#fff2b7";ctx.lineWidth=0.8;ctx.strokeRect(artX+2,artY+2,artW-4,artH-4);
  ctx.fillStyle="#b8282d";ctx.beginPath();ctx.moveTo(170,artY+artH-4);ctx.lineTo(175,artY+artH+1);ctx.lineTo(170,artY+artH+6);ctx.lineTo(165,artY+artH+1);ctx.closePath();ctx.fill();
  ctx.strokeStyle="#f5c972";ctx.stroke();
  const statsY=data.hasAbilities?250:279, statsH=42,stats=data.highlights;
  if(stats.length){
    const w=BW/stats.length;
    stats.forEach((item,index)=>{
      const x=BX+index*w;
      canvasBox(ctx,x,statsY,w,statsH,"#f9edcb","#ae783b");
      ctx.textAlign="center";ctx.fillStyle="#754726";
      drawFittedText(ctx,item.label.toUpperCase(),x+w/2,statsY+15,w-8,9,"'Cinzel',Georgia,serif","700");
      ctx.fillStyle="#22150e";
      drawFittedText(ctx,item.value,x+w/2,statsY+31,w-8,14,"'Spectral',Georgia,serif","700");
    });
  } else {
    canvasBox(ctx,BX,statsY,BW,statsH,"#f9edcb","#ae783b");
    ctx.fillStyle="#624122";ctx.font="9px Georgia,serif";ctx.fillText("I DATI COMPARRANNO QUI",22,statsY+24);
  }
  if(data.hasAbilities){
    const y=292,w=BW/6;
    data.abilities.forEach((item,index)=>{
      const x=BX+index*w;
      canvasBox(ctx,x,y,w,44,"#fff3d4","#ad814a");
      ctx.fillStyle="#6b4327";ctx.textAlign="center";
      ctx.font="700 8px Georgia,serif";ctx.fillText(item.label,x+w/2,y+16);
      ctx.fillStyle="#20150f";ctx.font="700 13px Georgia,serif";ctx.fillText(item.value,x+w/2,y+33,w-6);
    });
  }
  const notesY=data.hasAbilities?336:321,notesH=data.hasAbilities?125:140;
  const panel=ctx.createLinearGradient(0,notesY,0,notesY+notesH);
  panel.addColorStop(0,"#fff6db");panel.addColorStop(1,"#efd6a6");
  canvasBox(ctx,BX,notesY,BW,notesH,panel,"#a36d34");
  ctx.textAlign="left";let yy=notesY+17;
  data.details.forEach((item,index)=>{
    ctx.fillStyle="#5c351f";ctx.font="700 9px 'Cinzel',Georgia,serif";
    const str=item.label+": "+item.value;
    drawFittedText(ctx,str,23,yy,294,10,"'Spectral',Georgia,serif","600");
    yy+=15;
  });
  const description=data.description||"I dettagli appariranno dopo la selezione di un record.";
  ctx.fillStyle="#342014";ctx.font="italic 11px 'Spectral',Georgia,serif";
  const maxLines=Math.max(1,Math.min(5,Math.floor((notesY+notesH-yy-9)/13)));
  drawWrappedText(ctx,description,23,yy+3,card?.id?235:(data.dice?246:291),13,maxLines);
  if(data.dice){
    const diceX=23,diceY=notesY+notesH-29;
    canvasBox(ctx,diceX,diceY,68,25,"#8b1724","#e6b767");
    ctx.textAlign="center";ctx.fillStyle="#fff1ce";
    drawFittedText(ctx,data.dice,diceX+34,diceY+17,62,13,"'Cinzel',Georgia,serif","700");
  }
  // A saved card carries its QR on every fixed print/export path. Reuse the
  // real SVG-free QR canvas from the preview so no secondary QR generator drifts.
  const qr = element.querySelector('[data-card-qr] canvas');
  if (card?.id && qr) {
    try {
      ctx.fillStyle="#ffffff";
      ctx.fillRect(267,408,53,53);
      ctx.drawImage(qr,270,411,47,47);
      ctx.strokeStyle="#b07835";
      ctx.lineWidth=1;
      ctx.strokeRect(267,408,53,53);
    } catch {
      // Keep the card exportable even if a QR canvas is unavailable.
    }
  }
  // Exactly the same ornate asset is placed over the preview and the PNG/PDF.
  // Corners and vines occupy only the physical border and never cover data.
  try {
    const ornament = new Image();
    await new Promise((resolve, reject) => {
      ornament.onload = resolve;
      ornament.onerror = reject;
      ornament.src = data.hasAbilities ? REFERENCE_FRAME_URL : REFERENCE_FRAME_SIMPLE_URL;
      if (ornament.complete && ornament.naturalWidth > 0) resolve();
    });
    ctx.drawImage(ornament, 0, 0, width, height);
    // The supplied original has an old category plate beneath the parchment.
    // Its lettering is NEVER part of the dynamic front. Mask only that tiny
    // bottom interior strip, preserving gold corners and print bleed.
    {
      ctx.fillStyle="#2b0915";
      ctx.fillRect(18,463,304,12);
      const lowerMetal=ctx.createLinearGradient(18,463,322,463);
      lowerMetal.addColorStop(0,"#a8682c");
      lowerMetal.addColorStop(.35,"#ffdf91");
      lowerMetal.addColorStop(.7,"#cc873b");
      lowerMetal.addColorStop(1,"#9f5a25");
      ctx.strokeStyle=lowerMetal;ctx.lineWidth=2;ctx.beginPath();
      ctx.moveTo(18,462);ctx.lineTo(322,462);ctx.stroke();
    }
  } catch {
    // A browser that cannot rasterize SVG still gets the original gold border.
  }
  canvas.artworkDrawn=artworkDrawn;
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
