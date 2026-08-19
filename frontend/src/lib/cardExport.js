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

// One export path for both desktop and mobile. Waiting for fonts and artwork
// prevents the partial/unstyled canvas captures often seen on touch devices.
export async function captureCard(element, backgroundColor = "#0c0a09") {
  if (!element) throw new Error("Card render unavailable");
  if (document.fonts?.ready) await document.fonts.ready;
  await waitForImages(element);
  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  return html2canvas(element, {
    useCORS: true,
    allowTaint: false,
    backgroundColor,
    scale: Math.min(3, Math.max(2, window.devicePixelRatio || 2)),
    logging: false,
  });
}