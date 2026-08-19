// Physical card formats used by the A4 print-sheet exporter.
// All sizes are millimetres and preserve the 2.5:3.5 card ratio.
export const PRINT_FORMATS = Object.freeze({
  mini: Object.freeze({ label: "Mini", w: 44, h: 61.6, cols: 4, rows: 4 }),
  standard: Object.freeze({ label: "Standard", w: 63.5, h: 88.9, cols: 3, rows: 3 }),
  grande: Object.freeze({ label: "Grande", w: 86, h: 120.4, cols: 2, rows: 2 }),
});

export const A4_SIZE = Object.freeze({ w: 210, h: 297 });

export const getPrintSheetPositions = (format, count, mirror = false) => {
  const config = PRINT_FORMATS[format];
  if (!config) throw new Error(`Unknown print format: ${format}`);

  const safeCount = Math.max(0, Math.floor(Number(count) || 0));
  const gap = 3;
  const marginX = (A4_SIZE.w - (config.cols * config.w + (config.cols - 1) * gap)) / 2;
  const marginY = (A4_SIZE.h - (config.rows * config.h + (config.rows - 1) * gap)) / 2;

  return Array.from({ length: safeCount }, (_, index) => {
    const row = Math.floor(index / config.cols);
    const sourceColumn = index % config.cols;
    const col = mirror ? config.cols - 1 - sourceColumn : sourceColumn;
    return {
      x: marginX + col * (config.w + gap),
      y: marginY + row * (config.h + gap),
      w: config.w,
      h: config.h,
    };
  });
};