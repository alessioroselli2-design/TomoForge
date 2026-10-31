import {
  CARD_CANVAS_SIZE,
  addCharacterSheetPdfPages,
  addPrintSheetCard,
  addSingleCardA4PdfPages,
  addSingleCardPdfPages,
  createCardPng,
  getCardExportLayout,
  renderCardBackCanvas,
  renderCardCanvas,
} from "./cardExport";

const abilities = {
  for: "18",
  des: "14",
  cos: "16",
  int: "12",
  sag: "10",
  car: "8",
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
  clip: jest.fn(),
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
    querySelector: (selector) => (selector === "img" ? artwork : selector === "[data-card-qr] canvas" ? qr : null),
  };
};

describe("card export renderers", () => {
  let createElement;
  let canvases;
  let previousImage;

  beforeEach(() => {
    previousImage = global.Image;
    global.Image = class BackImageMock {
      complete = false;
      naturalWidth = 0;
      set src(value) {
        this._src = value;
        this.naturalWidth = 750;
        this.complete = true;
        this.onload?.();
      }
      get src() { return this._src; }
    };
    canvases = [];
    createElement = jest.spyOn(document, "createElement").mockImplementation((tag) => {
      if (tag !== "canvas") return { style: {} };
      const operations = [];
      const gradients = [];
      const context = createContext(operations, gradients);
      const canvas = {
        width: 0, height: 0,
        getContext: () => context,
        toDataURL: () => `data:image/png;base64,card-${canvases.length + 1}`,
        operations, gradients,
      };
      canvases.push(canvas);
      return canvas;
    });
  });

  afterEach(() => {
    createElement.mockRestore();
    global.Image = previousImage;
  });

  const written = (canvas) => canvas.operations.filter((op) => op.name === "fillText").map((op) => op.text).join(" ");

  it("renders new monster front with its six abilities, sourced stats and actual dice formula", async () => {
    const card = {
      id: "drago", type: "monster", name: "Drago Cremisi",
      attributes: { ...abilities, classe_armatura: "18", punti_ferita: "152", velocita: "12 m", tipo_creatura: "Drago", danno: "2d10 + 6", grado_sfida: "9" },
      description: "Un guardiano antico dalle scaglie cremisi.",
    };
    const front = await renderCardCanvas(makeExportElement(), card);
    const text = written(front);
    expect(front.artworkDrawn).toBe(true);
    expect(front.width).toBe(CARD_CANVAS_SIZE.width * CARD_CANVAS_SIZE.scale);
    expect(front.height).toBe(CARD_CANVAS_SIZE.height * CARD_CANVAS_SIZE.scale);
    ["Drago Cremisi", "CA", "18", "PF", "152", "12 m", "2d10+6",
      "FOR", "DES", "COS", "INT", "SAG", "CAR"].forEach((fragment) => expect(text).toContain(fragment));
    expect(front.operations.some((entry) => entry.name === "drawImage" && entry.args.at(-2) === 310 && entry.args.at(-1) === 166)).toBe(true);
    // Preview and the printed canvas must carry both original medallions.
    const statAssets=front.operations.filter(op=>op.name==="drawImage")
      .map(op=>op.args[0]?.src)
      .filter(src=>typeof src==="string" && src.includes("/card-art/stat-"));
    expect(statAssets).toEqual(["/card-art/stat-ca-clean-v24.svg","/card-art/stat-pf-clean-v24.svg"]);
    expect(text).toContain("Un guardiano antico");
    expect(front.operations.some((op) => op.name === "fillText" && op.y > 472)).toBe(false);
    expect(text).not.toContain("MOSTRO");
    // Every recorded movement mode is preserved by the print renderer.
    expect(text).toContain("12 m");
    expect(front.operations.some((op)=>op.name==="drawImage" && op.args.at(-2)===47 && op.args.at(-1)===47)).toBe(true);
  });

  it.each(["d4","d6","d8","d10","d12","d20"])("uses the correct %s illustrated jewel in export canvas", async(die)=>{
    const card={type:"class",name:"Classe",attributes:{dado_vita:die,abilita_primaria:"Forza"}};
    const element=makeExportElement();
    element.getAttribute=name=>name==="data-front-version"?"7":null;
    const canvas=await renderCardCanvas(element,card);
    const images=canvas.operations.filter(op=>op.name==="drawImage").map(op=>op.args[0]?.src);
    expect(images).toContain(`/card-art/class-dice/${die}-gem-v27.svg`);
    expect(written(canvas)).toContain(die);
    expect(images).not.toContain("/card-art/class-d10-gem-v26.svg");
  });

  it("prints the approved exact master image for a live v7 card, with no separate filigree", async () => {
    const el=makeExportElement();
    el.getAttribute=(name)=>name==="data-front-version"?"7":null;
    const card={id:"dragon",type:"monster",name:"Drago Rosso Adulto",
      attributes:{tipo_creatura:"Drago",grado_sfida:"17",classe_armatura:"19",punti_ferita:"256",
        velocita:"12 m",for:"27",des:"10",cos:"25",int:"16",sag:"13",car:"21"}};
    const front=await renderCardCanvas(el,card);
    const drawings=front.operations.filter(op=>op.name==="drawImage");
    const embedded=canvases.slice(1).flatMap(c=>c.operations.filter(op=>op.name==="drawImage"));
    expect(drawings[0].args[0].src).toBe("/card-art/front-master-v17.webp");
    expect(drawings.map(op=>op.args[0]?.src)).not.toContain("/card-art/front-detail-repair-v8.webp");
    expect(written(front)).toContain("Drago Rosso Adulto");
    const dragonDraw=embedded.find(op=>op.args[0]?.src==="/emblemi/drago-originale-hd-v2.webp");
    expect(dragonDraw).toBeDefined();
    const dragonOnMaster=drawings.find(op=>op.args[0]?.operations?.some(op=>op.args?.[0]?.src==="/emblemi/drago-originale-hd-v2.webp"));
    expect(dragonOnMaster.args.slice(-2)).toEqual([56,56]);

    const statDraws=drawings.filter(op=>/stat-(ca|pf)-clean-v24\.svg$/.test(op.args[0]?.src||""));
    expect(statDraws).toHaveLength(2);
    expect(statDraws[0].args.slice(-2)).toEqual([17,17]);
    expect(statDraws[1].args.slice(-2)).toEqual([17,17]);
    // Rune centers share the same baseline in the printed and preview versions.
    expect(statDraws[0].args.at(-3)).toBeCloseTo(195+19);
    expect(statDraws[1].args.at(-3)).toBeCloseTo(195+19);
    expect(statDraws[1].args.at(-4)-statDraws[0].args.at(-4)).toBeGreaterThan(90);
    expect(embedded.map(op=>op.args[0]?.src).filter(Boolean))
      .toEqual(expect.arrayContaining(["/emblemi/drago-originale-hd-v2.webp"]));
    expect(canvases.slice(1).some(c=>c.operations.some(op=>op.name==="fillRect")))
      .toBe(true);
    expect(written(front)).toContain("17");
    expect(written(front)).not.toContain("MOSTRI");
    expect(front.width).toBe(CARD_CANVAS_SIZE.width*CARD_CANVAS_SIZE.scale);
  });

  it("renders the spell-specific front without legacy color customization or fake dice", async () => {
    const card = {
      id: "fireball", type: "spell", name: "Palla di Fuoco",
      attributes: { livello: "3", scuola: "Invocazione", tempo_lancio: "1 azione", gittata: "45 m", danno: "8d6 fuoco" },
      description: "Un'esplosione di energia ignea investe la zona.",
      appearance: { title_effect: "rainbow", front_background_start: "#ff0000" },
    };
    const front = await renderCardCanvas(makeExportElement(), card);
    const text = written(front);
    ["Palla di Fuoco", "Invocazione", "8d6", "LIV.", "LANCIO", "GITTATA"].forEach((value) => expect(text).toContain(value));
    expect(front.gradients.flatMap(g => g.stops.map(s => s.color))).not.toContain("#ff0000");
    expect(front.operations.some((op) => op.name === "drawImage" && op.args.at(-1) === 195)).toBe(true);
  });

  it("keeps unchanged official backs, including the silver Personaggio variant", async () => {
    const back = await renderCardBackCanvas({ type: "character", back: { variant: "silver" } });
    const op = back.operations.find((entry) => entry.name === "drawImage");
    expect(op.args[0].src).toBe("/dorsi/personaggio-argento.jpg");
    expect(back.operations.some((entry) => entry.name === "fillText")).toBe(false);
  });

  it("letterboxes a nonstandard back instead of stretching its artwork", async () => {
    global.Image = class TallBackMock {
      complete = false; naturalWidth = 750; naturalHeight = 1200;
      set src(value) { this._src = value; this.complete = true; this.onload?.(); }
      get src() { return this._src; }
    };
    const back = await renderCardBackCanvas({ type: "spell" });
    const [, x, y, w, h] = back.operations.find((op) => op.name === "drawImage").args;
    expect(x).toBeGreaterThan(0);
    expect(y).toBe(0);
    expect(w / h).toBeCloseTo(750 / 1200);
  });

  it("shares one renderer between PNG, card PDF, duplex sheet, and A4 PDF", async () => {
    const card = { id: "person", type: "character", name: "Thalion",
      attributes: { ...abilities, classe: "Druido", livello: "5" }, back: { variant: "silver" } };
    const pdf = { addImage: jest.fn(), addPage: jest.fn() };
    const element = makeExportElement();
    const png = await createCardPng(element, card);
    const single = await addSingleCardPdfPages(pdf, element, card);
    const sheet = await addPrintSheetCard(pdf, element, card, {x: 12,y: 18,w:63.5,h:88.9});
    const a4 = await addSingleCardA4PdfPages(pdf, element, card);
    expect(written(png)).toContain("Thalion");
    expect(written(single.front)).toContain("Thalion");
    expect(written(sheet)).toContain("Thalion");
    expect(written(a4.front)).toContain("Thalion");
    expect(single.back.operations.find(op => op.name === "drawImage").args[0].src).toBe("/dorsi/personaggio-argento.jpg");
    expect(a4.back.operations.find(op => op.name === "drawImage").args[0].src).toBe("/dorsi/personaggio-argento.jpg");
    expect(getCardExportLayout(card).abilities).toHaveLength(6);
    expect(pdf.addImage).toHaveBeenCalledWith(expect.any(String), "PNG", 12, 18, 63.5, 88.9);
    expect(pdf.addImage).toHaveBeenCalledWith(expect.any(String), "PNG", 73.25, 104.05, 63.5, 88.9);
  });

  it("moves every long character-sheet list entry to additional A4 pages", async () => {
    const card = {
      id: "long-character-sheet",
      type: "character",
      name: "Personaggio con inventario esteso",
      attributes: {
        ...abilities,
        privilegi: Array.from({ length: 24 }, (_, index) => `Privilegio ${index + 1}`),
        incantesimi: Array.from({ length: 24 }, (_, index) => `Incantesimo ${index + 1}`),
        equipaggiamento: Array.from({ length: 24 }, (_, index) => `Equipaggiamento ${index + 1}`),
      },
    };
    const pdf = {
      addImage: jest.fn(),
      addPage: jest.fn(),
    };

    const pages = await addCharacterSheetPdfPages(pdf, card);
    const text = canvases
      .flatMap((canvas) => canvas.operations)
      .filter((entry) => entry.name === "fillText")
      .map((entry) => entry.text)
      .join(" ");

    expect(pages.length).toBeGreaterThan(1);
    expect(pdf.addImage).toHaveBeenCalledTimes(pages.length);
    expect(pdf.addPage).toHaveBeenCalledTimes(pages.length - 1);
    expect(text).toContain("Privilegio 24");
    expect(text).toContain("Incantesimo 24");
    expect(text).toContain("Equipaggiamento 24");
  });

  it("keeps a short character sheet on one A4 page", async () => {
    const card = {
      id: "short-character-sheet",
      type: "character",
      name: "Personaggio breve",
      attributes: { ...abilities, privilegi: ["Privilegio"], incantesimi: ["Incantesimo"], equipaggiamento: ["Equipaggiamento"] },
    };
    const pdf = {
      addImage: jest.fn(),
      addPage: jest.fn(),
    };

    const pages = await addCharacterSheetPdfPages(pdf, card);

    expect(pages).toHaveLength(1);
    expect(pdf.addPage).not.toHaveBeenCalled();
    expect(pdf.addImage).toHaveBeenCalledTimes(1);
  });


  it("keeps the artwork dimensions in preview-aligned cover-cropping", async () => {
    const artwork = { complete: true, naturalWidth: 270, naturalHeight: 200 };
    const element = {querySelectorAll: () => [artwork], querySelector: sel => sel === "img" ? artwork : null};
    const front = await renderCardCanvas(element, { type: "spell", name: "Tempesta", attributes: { livello: "3" } });
    const op = front.operations.find(e => e.name === "drawImage" && e.args[0] === artwork);
    expect(op.args).toHaveLength(9);
    expect(op.args.slice(-4)).toEqual([15, 84, 310, 195]);
    expect(front.artworkDrawn).toBe(true);
  });

  it("keeps the card and export functional when an artwork fails to load", async () => {
    const artwork = { complete: true, naturalWidth: 0 };
    const element = {querySelectorAll: () => [artwork], querySelector: sel => sel === "img" ? artwork : null};
    const front = await renderCardCanvas(element, { type: "item", name: "Spada", description: "Oggetto arcano." });
    expect(front.artworkDrawn).toBe(false);
    expect(front.operations.some(op => op.name === "fillRect" && op.x === 15 && op.y === 84)).toBe(true);
    expect(written(front)).toContain("Spada");
  });
});
