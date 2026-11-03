import { buildFrontBlueprint } from "@/lib/cardFrontBlueprint";
import { getFrontStatIcon } from "@/lib/frontStatIcons";
import { ORNATE_FRAME_URL } from "@/lib/ornateFrame";
import { FRONT_MASTER_URL, MASTER_REGIONS } from "@/lib/frontMaster";
import { categoryFrontLayout } from "@/lib/frontCategoryLayouts";
import { fitClassDescription } from "@/lib/classDescriptionFit";
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


/* Convert a pre-framed symbol into a soft inset so its baked-in metal rim
   never sits on top of the gold ring already engraved into the master.
   This reproduces the CSS radial mask in PNG and PDF output. */
function drawIntegratedMedallion(ctx, image, source, dest, fadeStart=.26, fadeEnd=.40) {
  const tile=document.createElement("canvas");
  tile.width=source.cell;tile.height=source.cell;
  const layer=tile.getContext("2d");
  const cropSize=source.cell/(source.zoom||1);
  const inset=(source.cell-cropSize)/2;
  layer.drawImage(image,source.x+inset,source.y+inset,cropSize,cropSize,
    0,0,source.cell,source.cell);
  const middle=source.cell/2;
  const feather=layer.createRadialGradient(middle,middle,source.cell*fadeStart,
    middle,middle,source.cell*fadeEnd);
  feather.addColorStop(0,"rgba(0,0,0,1)");
  feather.addColorStop(1,"rgba(0,0,0,0)");
  layer.globalCompositeOperation="destination-in";
  layer.fillStyle=feather;
  layer.fillRect(0,0,source.cell,source.cell);
  layer.globalCompositeOperation="source-over";
  ctx.drawImage(tile,dest.x-dest.size/2,dest.y-dest.size/2,dest.size,dest.size);
}

/* Print the same exact approved frame seen in the editor, with real text and
   true artwork, rather than drawing a second approximation of the design.
   Legacy projects lacking a v7 preview still use the original safe renderer. */
async function renderApprovedMaster(element,card) {
 const data=buildFrontBlueprint(card), {width,height,scale}=CARD_CANVAS_SIZE;
 const canvas=document.createElement("canvas");canvas.width=width*scale;canvas.height=height*scale;
 const ctx=canvas.getContext("2d");ctx.scale(scale,scale);
 const master=new Image();
 await new Promise((resolve,reject)=>{
   master.onload=resolve;master.onerror=()=>reject(new Error("Fronte artistico non disponibile"));
   master.src=FRONT_MASTER_URL;
   if(master.complete&&master.naturalWidth>0)resolve();
 });
 ctx.drawImage(master,0,0,width,height);
 // Independent interior layouts never replace or redraw the outer gold master.
 const layout=categoryFrontLayout(data.type);
 if(layout.interior){
   const inner=new Image();
   await new Promise((resolve,reject)=>{
     inner.onload=resolve;inner.onerror=()=>reject(new Error("Layout interno non disponibile"));
     inner.src=layout.interior;
     if(inner.complete&&inner.naturalWidth>0)resolve();
   });
   ctx.drawImage(inner,0,height*layout.interiorY,width,height*layout.interiorHeight);
 }
 // V17 is clean already. The old repair would misalign and blur the new artwork.
 const art=element.querySelector(".tf-v3-picture img");
 const g=MASTER_REGIONS.art;
 let artworkDrawn=false;
 if (art?.complete&&art.naturalWidth>0&&!art.getAttribute?.("src")?.includes("artwork-placeholder")) try {
   const iw=art.naturalWidth,ih=art.naturalHeight||iw;
   const fit=Math.max(g.w/iw,g.h/ih),sw=g.w/fit,sh=g.h/fit;
   ctx.drawImage(art,(iw-sw)/2,(ih-sh)/2,sw,sh,g.x,g.y,g.w,g.h);
   artworkDrawn=true;
 } catch {}
 // The card image, header badge and stat icons all use the same engraved
 // master coordinates as the CSS preview; never offset the source artwork.
 const icon=await loadFrontEmblem(data.emblem);
 if(icon&&data.emblem) {
   const s=data.emblem,m=MASTER_REGIONS.emblem;
   const dragon = s.sprite === "drago-hd";
   drawIntegratedMedallion(ctx,icon,
     {x:s.col*s.cell,y:s.row*s.cell,cell:s.cell,zoom:dragon?1.28:(data.type==="class"?(s.sprite==="guerriero-crest"?1.38:1.23):1.2)},
     {x:m.x,y:m.y,size:m.r*2},
     dragon?.37:.35,dragon?.48:.48);
 }
 ctx.fillStyle="#29180e";ctx.textAlign="center";
 drawFittedText(ctx,data.name,MASTER_REGIONS.title.x,MASTER_REGIONS.title.y+5,
   Math.min(MASTER_REGIONS.title.w,150),data.name.length>=27?14:data.name.length>=17?16:17.25,"'Cormorant Garamond',Georgia,serif","700");
 ctx.fillStyle="#4a2b1a";
 drawFittedText(ctx,data.subtitle,MASTER_REGIONS.subtitle.x,MASTER_REGIONS.subtitle.y-4,
   Math.min(MASTER_REGIONS.subtitle.w,142),7.7,"'Spectral',Georgia,serif","400");
 if(data.badge){
   ctx.fillStyle="#fff2db";ctx.font="700 8px Georgia,serif";
   ctx.fillText(data.badge.top,MASTER_REGIONS.badge.x,37);
   drawFittedText(ctx,data.badge.value,MASTER_REGIONS.badge.x,51,44,22,"Georgia,serif","700");
 }
 const statY=MASTER_REGIONS.stats.y;
 const statImages=await Promise.all(data.highlights.map(async it=>{
   const src=getFrontStatIcon(it.label);
   if(!src)return null;
   const im=new Image();try {
     await new Promise((resolve,reject)=>{im.onload=resolve;im.onerror=reject;im.src=src;
       if(im.complete&&im.naturalWidth>0)resolve()});
     return im;
   } catch {return null;}
 }));
 const sx=MASTER_REGIONS.stats.x, widths=[.32,.35,.33].map(f=>f*MASTER_REGIONS.stats.w);
 data.highlights.slice(0,3).forEach((it,i)=>{
   const cellW=widths[i]||widths[2],cx=sx+widths.slice(0,i).reduce((a,b)=>a+b,0)+cellW/2,icon=statImages[i];
   const labelCenter=cx;
   const max=cellW-12;
   let valueCenter=cx,valueMaxWidth=max;
   if(data.type==="class"){
     ctx.textAlign="center";ctx.fillStyle="#51301c";
     drawFittedText(ctx,it.label,cx,statY+10,max,7.3,"Georgia,serif","700");
     const left=cx-cellW/2+9;
     if(icon)ctx.drawImage(icon,left,statY+20,14,14);
     ctx.fillStyle="#1d140c";ctx.font="700 7.4px Georgia,serif";
     const maxText=cellW-(icon?32:15);
     const lines=wrapTextLines(ctx,it.value,maxText).slice(0,4);
     const first=statY+23-(lines.length-1)*2.1;
     ctx.textAlign="left";
     lines.forEach((line,n)=>ctx.fillText(line,left+(icon?17:0),first+n*7.9,maxText));
     return;
   }
   if(icon&&data.type!=="class"){
     // Exactly the same centered [rune + 5px gap + value] flex group as CSS.
     const runeSize=17,gap=5;
     ctx.font="700 14px Georgia,serif";
     const renderedTextWidth=Math.min(ctx.measureText(it.value).width,max-runeSize-gap);
     const groupWidth=runeSize+gap+renderedTextWidth;
     const runeLeft=cx-groupWidth/2;
     ctx.drawImage(icon,runeLeft,statY+19,runeSize,runeSize);
     valueCenter=runeLeft+runeSize+gap+renderedTextWidth/2;
     valueMaxWidth=Math.max(12,renderedTextWidth);
   }
   ctx.textAlign="center";ctx.fillStyle="#51301c";
   drawFittedText(ctx,it.label,labelCenter,statY+11,max,it.label==="Vel."?7.5:9,"Georgia,serif","700");
   ctx.fillStyle="#1d140c";
   if(it.label==="Vel.") {
     // Full movement modes, no ellipsis or line clipped by the parchment border.
     ctx.font="700 7.8px Georgia,serif";
     const lines=wrapTextLines(ctx,it.value,max-3).slice(0,3);
     const first=statY+(lines.length===1?30:lines.length===2?26:21);
     lines.forEach((line,n)=>ctx.fillText(line,labelCenter,first+n*8,max-3));
   } else {
     drawFittedText(ctx,it.value,valueCenter,statY+32,valueMaxWidth,icon?14:13,"Georgia,serif","700");
   }
 });
 data.abilities.slice(0,6).forEach((it,i)=>{
   const cx=MASTER_REGIONS.abilities.x+(i+.5)*MASTER_REGIONS.abilities.w/6;
   ctx.fillStyle="#402418";ctx.textAlign="center";ctx.font="700 8px Georgia,serif";
   ctx.fillText(it.label,cx,MASTER_REGIONS.abilities.y+15);
   ctx.fillStyle="#23150f";
   drawFittedText(ctx,it.value,cx,MASTER_REGIONS.abilities.y+32,MASTER_REGIONS.abilities.w/6-5,10,"Georgia,serif","700");
 });
 const details=layout.showDetails ? data.details.slice(0,2) : [];
 details.forEach((d,i)=>{
   const x=MASTER_REGIONS.detail.x+8+i*152;
   const detailW=data.spellDieAsset&&i===1?87:136;
   ctx.fillStyle="#2d190e";ctx.textAlign="left";
   drawFittedText(ctx,d.label,x,MASTER_REGIONS.detail.y+12,detailW,9,"Georgia,serif","700");
   ctx.font="9px Spectral,Georgia,serif";
   drawWrappedText(ctx,d.value,x,MASTER_REGIONS.detail.y+27,detailW,11,2);
 });
 const desc=(data.type==="class"?data.fullDescription:data.description)||"I dettagli appariranno dopo la selezione di un record.";
 if(data.type==="class"){
   // Print exactly the maximum number of complete sentences that fit.
   // No scrollable text and no sentence cut at an arbitrary character count.
   const x=32,y=260,w=195,h=169,fontSize=9,lineHeight=10.53;
   ctx.font=`${fontSize}px Spectral,Georgia,serif`;
   const fitted=fitClassDescription(desc,text=>
     wrapTextLines(ctx,text,w).length*lineHeight<=h);
   const lines=wrapTextLines(ctx,fitted,w);
   ctx.fillStyle="#2d190e";ctx.textAlign="left";
   lines.forEach((line,i)=>ctx.fillText(line,x,y+i*lineHeight,w));
   if(data.classDieAsset){
     const jewel=await loadFrontEmblem({src:data.classDieAsset});
     if(jewel)ctx.drawImage(jewel,240,335,72,75);
   }
 } else {
   ctx.fillStyle="#2d190e";ctx.textAlign="left";ctx.font="700 10px Georgia,serif";
   if(data.showDescriptionLabel)ctx.fillText("Descrizione",MASTER_REGIONS.description.x+8,MASTER_REGIONS.description.y+11);
   ctx.font="10px Spectral,Georgia,serif";
   drawWrappedText(ctx,desc,MASTER_REGIONS.description.x+8,
     MASTER_REGIONS.description.y+(data.showDescriptionLabel?27:17),
     data.spellDieAsset?201:(card?.id?244:287),12,5);
 }
 if(data.type==="monster"&&data.dice){
   ctx.fillStyle="#3c2013";ctx.textAlign="left";
   drawFittedText(ctx,data.dice,MASTER_REGIONS.description.x+16,
     MASTER_REGIONS.description.y+103,66,10,"Georgia,serif","700");
 }
 if(data.spellDieAsset){
   const jewel=await loadFrontEmblem({src:data.spellDieAsset});
   // The art has its original die label engraved; draw the actual spell formula
   // on a separate parchment slip, never overprint the ruby image.
   if(jewel)ctx.drawImage(jewel,239,342,78,81);
   // A single print-layer formula at the geometric center, matching Safari.
   // No detached parchment label and no pre-engraved text in the spell gem.
   ctx.textAlign="center";ctx.fillStyle="#fff2d6";
   ctx.shadowColor="#26051a";ctx.shadowBlur=2;ctx.shadowOffsetY=1;
   drawFittedText(ctx,data.dice,278,389,64,18,"Georgia,serif","700");
   ctx.shadowBlur=0;ctx.shadowOffsetY=0;
 }
 const qr=element.querySelector('[data-card-qr] canvas');
 if(card?.id&&qr)try {
   const qrX=data.type==="class"?286:(data.spellDieAsset?280:278);
   const qrY=data.type==="class"?415:(data.spellDieAsset?285:414);
   const qrSize=data.type==="class"?22:(data.spellDieAsset?33:42);
   ctx.fillStyle="#fff";ctx.fillRect(qrX,qrY,qrSize,qrSize);
   ctx.drawImage(qr,qrX+3,qrY+3,qrSize-6,qrSize-6);
   ctx.strokeStyle="#b37c38";ctx.lineWidth=1;ctx.strokeRect(qrX,qrY,qrSize,qrSize);
 }catch{}
 canvas.artworkDrawn=artworkDrawn;return canvas;
}

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
// All cards, including legacy records without a preview version tag, now
// render with the SAME approved Monster v17 raster. No procedural fallback.
export async function renderCardCanvas(element,card){
 if(!element)throw new Error("Card render unavailable");
 await waitForImages(element);
 if(document.fonts?.ready)await document.fonts.ready;
 return renderApprovedMaster(element,card);
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
