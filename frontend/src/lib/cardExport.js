import html2canvas from "html2canvas";
import { QUICK_FIELDS, attrLabel } from "@/lib/cardTypes";

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

const imageToDataUrl = async (image) => {
  if (!image) return null;
  try {
    if (!image.complete) {
      await new Promise((resolve) => {
        image.addEventListener("load", resolve, { once: true });
        image.addEventListener("error", resolve, { once: true });
      });
    }
    const canvas = document.createElement("canvas");
    canvas.width = image.naturalWidth || image.width;
    canvas.height = image.naturalHeight || image.height;
    if (!canvas.width || !canvas.height) return null;
    canvas.getContext("2d").drawImage(image, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.92);
  } catch {
    return null;
  }
};

// PDF-native assets: artwork and QR are images, while all card text is drawn
// by jsPDF. This avoids browser DOM/font rasterization entirely for print
// sheets, especially on iOS Safari.
export async function getCardExportAssets(element) {
  if (!element) throw new Error("Card render unavailable");
  await waitForImages(element);
  const image = element.querySelector("img");
  const qr = element.querySelector("canvas");
  return {
    artwork: await imageToDataUrl(image),
    qr: qr?.toDataURL("image/png") || null,
  };
}

const exportFields = (card) => {
  const attrs = card.attributes || {};
  const has = (key) => {
    const value = attrs[key];
    return (typeof value === "string" || typeof value === "number") && String(value).trim() !== "";
  };
  let keys = (QUICK_FIELDS[card.type] || []).filter(has);
  if (!keys.length) keys = Object.keys(attrs).filter((key) => has(key)).slice(0, 4);
  return keys.slice(0, 4).map((key) => [attrLabel(key), String(attrs[key])]);
};

const drawFittedText = (ctx, text, x, y, maxWidth, size, family, weight = "400") => {
  let currentSize = size;
  do {
    ctx.font = `${weight} ${currentSize}px ${family}`;
    currentSize -= 0.5;
  } while (currentSize > 8 && ctx.measureText(text).width > maxWidth);
  ctx.fillText(text, x, y);
};

// Dedicated raster renderer for A4 sheets. It mirrors the card composition
// but never asks the browser to screenshot a flex/overflow DOM tree.
export async function renderCardCanvas(element, card) {
  if (!element) throw new Error("Card render unavailable");
  await waitForImages(element);
  if (document.fonts?.ready) await document.fonts.ready;

  const scale = 3;
  const width = 340;
  const height = 476;
  const canvas = document.createElement("canvas");
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);
  ctx.fillStyle = "#151311";
  ctx.fillRect(0, 0, width, height);

  const frameColors = {
    gold: ["#6b4612", "#fff3a4", "#b87c16"],
    silver: ["#535c66", "#f7fbff", "#9ca9b8"],
    rainbow: ["#ed4f6f", "#f7cc52", "#59b9ee"],
  }[card.frame || "gold"] || ["#6b4612", "#fff3a4", "#b87c16"];
  const border = ctx.createLinearGradient(0, 0, width, height);
  frameColors.forEach((color, index) => border.addColorStop(index / (frameColors.length - 1), color));
  ctx.strokeStyle = border;
  ctx.lineWidth = 3;
  ctx.strokeRect(1.5, 1.5, width - 3, height - 3);

  const gold = "#f8d764";
  const light = "#f5f1df";
  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = gold;
  drawFittedText(ctx, String(card.name || "Senza nome"), 12, 32, 250, 18, "'Cormorant Garamond', Georgia, serif", "700");
  ctx.font = "600 10px 'Cinzel', Georgia, serif";
  ctx.textAlign = "right";
  ctx.fillText(String(card.custom_type || card.type || "").toUpperCase(), 328, 30);
  ctx.textAlign = "left";

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

  const fields = exportFields(card);
  const statY = 299;
  const cellW = 154;
  const cellH = 31;
  fields.forEach(([label, value], index) => {
    const col = index % 2;
    const row = Math.floor(index / 2);
    const cellX = 12 + col * 162;
    const cellY = statY + row * 38;
    ctx.strokeStyle = "#b4933c";
    ctx.strokeRect(cellX, cellY, cellW, cellH);
    ctx.textAlign = "left";
    ctx.fillStyle = gold;
    ctx.font = "700 8px 'Cinzel', Georgia, serif";
    ctx.fillText(label.toUpperCase(), cellX + 7, cellY + 12);
    ctx.fillStyle = light;
    ctx.font = "400 11px 'Spectral', Georgia, serif";
    ctx.fillText(value, cellX + 7, cellY + 25, cellW - 14);
  });

  const description = String(card.description || "").trim();
  if (description) {
    ctx.fillStyle = light;
    ctx.font = "italic 10px 'Spectral', Georgia, serif";
    const words = description.split(/\s+/);
    const lines = [];
    let line = "";
    words.forEach((word) => {
      const next = line ? `${line} ${word}` : word;
      if (ctx.measureText(next).width > 316 && line) {
        lines.push(line);
        line = word;
      } else line = next;
    });
    if (line) lines.push(line);
    lines.slice(0, 2).forEach((value, index) => ctx.fillText(value, 12, 380 + index * 14));
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

// One export path for both desktop and mobile. Waiting for fonts and artwork
// prevents the partial/unstyled canvas captures often seen on touch devices.
export async function captureCard(element, backgroundColor = "#0c0a09") {
  if (!element) throw new Error("Card render unavailable");
  // The export nodes live outside the viewport. Capturing a node whose
  // bounding rect is around -99999px makes some browsers offset its children
  // inside the canvas. Move only the captured root to a neutral viewport
  // position while rendering, then restore every inline style immediately.
  const styleKeys = ["position", "left", "top", "right", "bottom", "margin", "transform", "z-index"];
  const previousStyles = Object.fromEntries(styleKeys.map((key) => [
    key,
    [element.style.getPropertyValue(key), element.style.getPropertyPriority(key)],
  ]));
  styleKeys.forEach((key) => element.style.removeProperty(key));
  element.style.setProperty("position", "fixed", "important");
  element.style.setProperty("left", "0px", "important");
  element.style.setProperty("top", "0px", "important");
  element.style.setProperty("margin", "0", "important");
  element.style.setProperty("transform", "none", "important");
  element.style.setProperty("z-index", "2147483647", "important");

  try {
    if (document.fonts?.ready) await document.fonts.ready;
    await waitForImages(element);
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const isAppleTouch = /iPad|iPhone|iPod/.test(navigator.userAgent)
      || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    return await html2canvas(element, {
      useCORS: true,
      allowTaint: false,
      backgroundColor,
      // iOS Safari can clip web-font glyphs when html2canvas supersamples a
      // card at 3x/4x. The PDF receives the same physical dimensions, so a
      // 1x source is preferable to a high-resolution source with broken text.
      scale: isAppleTouch ? 1 : Math.min(3, Math.max(2, window.devicePixelRatio || 2)),
      logging: false,
      scrollX: 0,
      scrollY: 0,
    });
  } finally {
    styleKeys.forEach((key) => {
      const [value, priority] = previousStyles[key];
      if (value) element.style.setProperty(key, value, priority);
      else element.style.removeProperty(key);
    });
  }
}