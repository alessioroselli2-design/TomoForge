// One physical edge for every approved front and reverse. The artwork is
// uniformly reduced, not stretched or clipped; all interior designs stay intact.
export const CARD_EDGE_COLOR = "#101019";
export const CARD_ART_INSET = 0.02;
export const CARD_ART_SCALE = 1 - 2 * CARD_ART_INSET;

// Class is the only approved 750 x 1050 reverse photographed with extra
// top/bottom/right margins. Crop only the surplus surround, not the design.
// The 725 x 1015 source window has exactly the 5:7 print aspect ratio.
const CLASS_BACK_SOURCE = Object.freeze({ x: 0, y: 16, w: 725, h: 1015 });
const SOURCE_WIDTH = 750;
const SOURCE_HEIGHT = 1050;

export function getBackCrop(file, width, height) {
  if (file !== "classe" || Math.abs(width / height - 5 / 7) > 0.001) return null;
  const scale = width / SOURCE_WIDTH;
  return {
    x: CLASS_BACK_SOURCE.x * scale, y: CLASS_BACK_SOURCE.y * scale,
    w: CLASS_BACK_SOURCE.w * scale, h: CLASS_BACK_SOURCE.h * scale,
  };
}

export function backImageStyle(file) {
  const crop = getBackCrop(file, SOURCE_WIDTH, SOURCE_HEIGHT);
  if (!crop) return { inset: 0, width: "100%", height: "100%", objectFit: "contain" };
  return {
    left: -100 * crop.x / crop.w + "%",
    top: -100 * crop.y / crop.h + "%",
    width: 100 * SOURCE_WIDTH / crop.w + "%",
    height: 100 * SOURCE_HEIGHT / crop.h + "%",
    maxWidth: "none", // Tailwind preflight must not shrink the calibrated crop.
    objectFit: "contain",
  };
}

export function cardArtBounds(width, height) {
  return { x: width * CARD_ART_INSET, y: height * CARD_ART_INSET,
    w: width * CARD_ART_SCALE, h: height * CARD_ART_SCALE };
}

// Apply the exact preview geometry to the finished raster, including the
// legacy canvas path and dedicated DOM paths. Draw the existing canvas into
// itself (the canvas spec snapshots its source for overlapping draws).
export function applyCardPrintEdge(canvas) {
  const ctx = canvas.getContext("2d");
  const { width, height } = canvas;
  const { x, y, w, h } = cardArtBounds(width, height);
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalCompositeOperation = "copy";
  ctx.drawImage(canvas, x, y, w, h);
  ctx.globalCompositeOperation = "destination-over";
  ctx.fillStyle = CARD_EDGE_COLOR;
  ctx.fillRect(0, 0, width, height);
  ctx.restore();
  return canvas;
}
