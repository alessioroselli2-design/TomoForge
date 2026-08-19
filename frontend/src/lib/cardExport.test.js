import {
  CARD_CANVAS_SIZE,
  addPrintSheetCard,
  addSingleCardPdfPages,
  createCardPng,
  getCardExportLayout,
  renderCardBackCanvas,
  renderCardCanvas,
} from "./cardExport";

jest.mock("html2canvas", () => jest.fn());

const sixQuickStats = {
  livello: "5",
  area: "18 metri",
  azione: "Azione",
  tempo_lancio: "1 azione",
  concentrazione: "Sì",
  danno: "8d6 fuoco",
};

const abilities = {
  for: "18",
  des: "14",
  cos: "16",
  int: "12",
  sag: "10",
  car: "8",
};

const configuredBack = {
  style: "runic",
  color: "#2563eb",
  emblem: "dragon",
  motto: "Dove il fuoco incontra l'inchiostro",
};

const createContext = (operations, gradients) => ({
  font: "10px serif",
  fillStyle: "",
  strokeStyle: "",
  textAlign: "left",
  textBaseline: "alphabetic",
  scale: (x, y) => operations.push({ name: "scale", x, y }),
  fillRect(x, y, w, h) {
    operations.push({ name: "fillRect", x, y, w, h, fillStyle: this.fillStyle });
  },
  strokeRect: (x, y, w, h) => operations.push({ name: "strokeRect", x, y, w, h }),
  fillText: (text, x, y, maxWidth) => operations.push({
    name: "fillText", text: String(text), x, y, maxWidth,
  }),
  drawImage: (...args) => operations.push({ name: "drawImage", args }),
  measureText(text) {
    const size = Number((this.font.match(/([\d.]+)px/) || [, 10])[1]);
    return { width: String(text).length * size * 0.48 };
  },
  createLinearGradient: () => {
    const gradient = {
      stops: [],
      addColorStop(offset, color) {
        this.stops.push({ offset, color });
      },
    };
    gradients.push(gradient);
    return gradient;
  },
  createRadialGradient: () => ({
    addColorStop: jest.fn(),
  }),
  save: jest.fn(),
  restore: jest.fn(),
  translate: jest.fn(),
  rotate: jest.fn(),
  beginPath: jest.fn(),
  closePath: jest.fn(),
  arc: jest.fn(),
  moveTo: jest.fn(),
  lineTo: jest.fn(),
  quadraticCurveTo: jest.fn(),
  bezierCurveTo: jest.fn(),
  stroke() {
    operations.push({ name: "stroke", strokeStyle: this.strokeStyle });
  },
  fill() {
    operations.push({ name: "fill", fillStyle: this.fillStyle });
  },
});

const makeExportElement = () => {
  const artwork = { complete: true, naturalWidth: 680, naturalHeight: 952 };
  const qr = { toDataURL: () => "data:image/png;base64,qr" };
  return {
    querySelectorAll: () => [artwork],
    querySelector: (selector) => (selector === "img" ? artwork : selector === "canvas" ? qr : null),
  };
};

describe("card export renderers", () => {
  let createElement;
  let canvases;

  beforeEach(() => {
    canvases = [];
    createElement = jest.spyOn(document, "createElement").mockImplementation((tag) => {
      if (tag !== "canvas") return { style: {} };
      const operations = [];
      const gradients = [];
      const context = createContext(operations, gradients);
      const canvas = {
        width: 0,
        height: 0,
        getContext: () => context,
        toDataURL: () => `data:image/png;base64,card-${canvases.length + 1}`,
        operations,
        gradients,
      };
      canvases.push(canvas);
      return canvas;
    });
  });

  afterEach(() => createElement.mockRestore());

  it("renders all six quick statistics and the description within the PNG/PDF safe area", async () => {
    const card = {
      id: "spell-six-stats",
      type: "spell",
      name: "Tempesta del Drago Cremisi",
      frame: "rainbow",
      appearance: { title_effect: "gold", description_opacity: 0.8 },
      attributes: sixQuickStats,
      description: "Una descrizione abbastanza lunga da richiedere due righe ma non deve invadere il footer.",
      back: configuredBack,
    };

    const canvas = await renderCardCanvas(makeExportElement(), card);
    const text = canvas.operations.filter((entry) => entry.name === "fillText").map((entry) => entry.text).join(" ");
    const descriptionPanel = canvas.operations
      .filter((entry) => entry.name === "fillRect" && entry.x === 12 && entry.w === 250)
      .at(-1);

    expect(canvas.width).toBe(CARD_CANVAS_SIZE.width * CARD_CANVAS_SIZE.scale);
    expect(canvas.height).toBe(CARD_CANVAS_SIZE.height * CARD_CANVAS_SIZE.scale);
    expect(text).toContain("Tempesta del Drago Cremisi");
    expect(text).toContain("MAGIA");
    Object.entries(sixQuickStats).forEach(([label, value]) => {
      expect(text).toContain(value);
      expect(text).toContain(label === "tempo_lancio" ? "TEMPO DI LANCIO" : label.toUpperCase());
    });
    expect(text).toContain("Una descrizione abbastanza lunga");
    expect(descriptionPanel.y + descriptionPanel.h).toBeLessThanOrEqual(444);
    expect(Math.max(...canvas.operations
      .filter((entry) => entry.name === "fillText")
      .map((entry) => entry.y))).toBeLessThanOrEqual(466);
  });

  it.each(["monster", "character"])(
    "renders six ability scores, type, description, and configured back for %s cards",
    async (type) => {
      const card = {
        id: `${type}-abilities`,
        type,
        name: type === "monster" ? "Custode di Ossidiana" : "Aralda delle Rune",
        frame: "silver",
        appearance: { title_effect: "silver" },
        attributes: {
          ...abilities,
          classe_armatura: "17",
          punti_ferita: "120",
          grado_sfida: "8",
          velocita: "9 m",
        },
        description: "Difende il sigillo antico con potenza e disciplina.",
        back: configuredBack,
      };

      const front = await renderCardCanvas(makeExportElement(), card);
      const back = await renderCardBackCanvas(card);
      const frontText = front.operations.filter((entry) => entry.name === "fillText").map((entry) => entry.text).join(" ");
      const backText = back.operations.filter((entry) => entry.name === "fillText").map((entry) => entry.text).join(" ");

      expect(getCardExportLayout(card).abilities).toHaveLength(6);
      ["FOR", "DES", "COS", "INT", "SAG", "CAR", ...Object.values(abilities)].forEach((value) => {
        expect(frontText).toContain(value);
      });
      expect(frontText).toContain(type === "monster" ? "MOSTRO" : "PERSONAGGIO");
      expect(frontText).toContain("Difende il sigillo antico");
      expect(backText).toContain("TOME · FORGE");
      expect(backText).toContain("Dove il fuoco incontra");
      expect(backText).not.toContain(type === "monster" ? "MOSTRO" : "PERSONAGGIO");
      expect(backText).toContain("ᚱ");
      expect(backText).toContain("♜");
      expect(back.operations.some((entry) => entry.name === "stroke" && entry.strokeStyle === configuredBack.color)).toBe(true);
      expect(Math.max(...back.operations
        .filter((entry) => entry.name === "fillText")
        .map((entry) => entry.y))).toBeLessThanOrEqual(CARD_CANVAS_SIZE.height);
    },
  );

  it.each([
    ["gold", ["#fffbd1", "#f8d764", "#c98b18"]],
    ["silver", ["#ffffff", "#cbd5e1", "#64748b"]],
    ["rainbow", ["#fb7185", "#facc15", "#34d399", "#60a5fa", "#c084fc"]],
    ["crimson", ["#ffe4e6", "#fb7185", "#881337"]],
    ["azure", ["#e0f2fe", "#38bdf8", "#1e3a8a"]],
    ["violet", ["#f3e8ff", "#c084fc", "#581c87"]],
    ["emerald", ["#d1fae5", "#34d399", "#064e3b"]],
    ["copper", ["#ffedd5", "#fb923c", "#7c2d12"]],
  ])("keeps the %s title effect in the fixed export renderer", async (titleEffect, expectedColors) => {
    await renderCardCanvas(makeExportElement(), {
      id: `title-${titleEffect}`,
      type: "spell",
      name: "Titolo con effetto",
      frame: "gold",
      appearance: { title_effect: titleEffect },
      attributes: { livello: "1" },
    });

    const colors = canvases[0].gradients.flatMap((gradient) => gradient.stops.map((stop) => stop.color));
    expect(colors).toEqual(expect.arrayContaining(expectedColors));
  });

  it("keeps custom text-panel and text colors in the fixed export renderer", async () => {
    const card = {
      id: "contrast-colors",
      type: "spell",
      name: "Inchiostro di Luna",
      frame: "gold",
      appearance: {
        text_panel_color: "#0b1d31",
        text_color: "#dbeafe",
        description_opacity: 0.85,
      },
      attributes: { livello: "2" },
      description: "Il testo deve conservare il contrasto scelto dall'utente.",
    };

    const canvas = await renderCardCanvas(makeExportElement(), card);
    const descriptionPanel = canvas.operations
      .filter((entry) => entry.name === "fillRect" && entry.x === 12 && entry.w === 250)
      .at(-1);
    const text = canvas.operations.filter((entry) => entry.name === "fillText").map((entry) => entry.text).join(" ");

    expect(descriptionPanel.fillStyle).toBe("rgba(11, 29, 49, 0.85)");
    expect(text).toContain("Il testo deve conservare");
  });

  it("uses the same dedicated front/back renderer for PNG, single PDF, and A4 sheet exports", async () => {
    const card = {
      id: "all-export-paths",
      type: "character",
      name: "Esportazione completa",
      frame: "rainbow",
      appearance: { title_effect: "rainbow" },
      attributes: { ...abilities, classe: "Mago", livello: "8" },
      description: "Il contenuto completo resta nel canvas su ogni formato.",
      back: configuredBack,
    };
    const pdf = {
      addImage: jest.fn(),
      addPage: jest.fn(),
    };
    const bounds = { x: 12, y: 18, w: 63.5, h: 88.9 };

    const png = await createCardPng(makeExportElement(), card);
    const singleCard = await addSingleCardPdfPages(pdf, makeExportElement(), card);
    const sheetFront = await addPrintSheetCard(pdf, makeExportElement(), card, bounds);
    const sheetBack = await addPrintSheetCard(pdf, null, card, { ...bounds, x: 134.5 }, true);

    expect(png.operations.some((entry) => entry.name === "strokeRect" && entry.x === 1.5)).toBe(true);
    expect(singleCard.front.operations.some((entry) => entry.name === "fillText" && entry.text === "PERSONAGGIO")).toBe(true);
    expect(singleCard.back.operations.some((entry) => entry.name === "fillText" && entry.text === "♜")).toBe(true);
    expect(singleCard.back.operations.some((entry) => entry.name === "fillText" && entry.text === "GRIMORIO ARCANO")).toBe(false);
    expect(sheetFront.operations.some((entry) => entry.name === "fillText" && entry.text === "FOR")).toBe(true);
    expect(sheetBack.operations.some((entry) => entry.name === "stroke" && entry.strokeStyle === configuredBack.color)).toBe(true);
    expect(pdf.addPage).toHaveBeenCalledWith([63.5, 88.9], "portrait");
    expect(pdf.addImage).toHaveBeenCalledWith(expect.any(String), "PNG", 0, 0, 63.5, 88.9);
    expect(pdf.addImage).toHaveBeenCalledWith(expect.any(String), "PNG", 12, 18, 63.5, 88.9);
    expect(pdf.addImage).toHaveBeenCalledWith(expect.any(String), "PNG", 134.5, 18, 63.5, 88.9);
  });
});