import html2canvas from "html2canvas";

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