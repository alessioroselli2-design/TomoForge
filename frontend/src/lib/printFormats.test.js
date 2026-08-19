import { A4_SIZE, getPrintSheetPositions, PRINT_FORMATS } from "./printFormats";

describe("A4 print formats", () => {
  it.each([
    ["mini", 4, 4, 44, 61.6],
    ["standard", 3, 3, 63.5, 88.9],
    ["grande", 2, 2, 86, 120.4],
  ])("keeps %s cards entirely inside A4", (format, cols, rows, width, height) => {
    const config = PRINT_FORMATS[format];
    const positions = getPrintSheetPositions(format, cols * rows);

    expect(config).toMatchObject({ cols, rows, w: width, h: height });
    expect(positions).toHaveLength(cols * rows);
    positions.forEach((position) => {
      expect(position.x).toBeGreaterThanOrEqual(0);
      expect(position.y).toBeGreaterThanOrEqual(0);
      expect(position.x + position.w).toBeLessThanOrEqual(A4_SIZE.w);
      expect(position.y + position.h).toBeLessThanOrEqual(A4_SIZE.h);
    });
  });

  it("mirrors back positions for long-edge duplex printing", () => {
    const fronts = getPrintSheetPositions("standard", 3);
    const backs = getPrintSheetPositions("standard", 3, true);

    expect(backs.map(({ x }) => x)).toEqual(fronts.map(({ x }) => x).reverse());
    expect(backs.map(({ y }) => y)).toEqual(fronts.map(({ y }) => y));
  });

  it("rejects an unknown physical format instead of silently producing a clipped sheet", () => {
    expect(() => getPrintSheetPositions("unknown", 1)).toThrow("Unknown print format");
  });
});