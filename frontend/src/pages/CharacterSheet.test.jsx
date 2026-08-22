import React, { act } from "react";
import { readFileSync } from "fs";
import { resolve } from "path";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { api } from "@/lib/api";
import CharacterSheet from "./CharacterSheet";

global.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock("@/lib/api", () => ({
  api: { get: jest.fn(), put: jest.fn() },
}));

jest.mock("@/components/Navbar", () => () => <nav />);

jest.mock("sonner", () => ({
  toast: {
    error: jest.fn(),
    message: jest.fn(),
    success: jest.fn(),
  },
}));

const emptyCharacter = {
  id: "empty-character",
  type: "character",
  name: "",
  attributes: {},
};

const typicalCharacter = {
  id: "typical-character",
  type: "character",
  name: "Lia della Torre",
  attributes: {
    livello: "5",
    razza: "Elfa",
    classe: "Maga",
    classe_armatura: "14",
    punti_ferita: "32",
    for: "8",
    des: "14",
    cos: "13",
    int: "18",
    sag: "12",
    car: "10",
    incantesimi: ["Dardo incantato", "Scudo"],
    equipaggiamento: ["Bastone", "Libro degli incantesimi"],
  },
};

const richCharacter = {
  id: "rich-character",
  type: "character",
  name: "Alyndra-la-Custode-della-Conoscenza-Senza-Confini",
  description: "Una storia molto lunga che deve restare nel riquadro anche quando il testo continua oltre una riga normale.",
  attributes: {
    ...typicalCharacter.attributes,
    privilegi: Array.from({ length: 10 }, (_, index) => `Privilegio ${index + 1}`),
    incantesimi: Array.from({ length: 18 }, (_, index) => `Incantesimo di prova ${index + 1}`),
    equipaggiamento: Array.from({ length: 18 }, (_, index) => `Equipaggiamento di prova ${index + 1}`),
    linguaggi: ["Comune", "Elfico", "Draconico", "Infernale"],
    competenze_armi: "Arco-lungo-con-un-identificatore-molto-lungo-senza-spazi",
  },
};

describe("CharacterSheet printable layout", () => {
  let container;
  let root;

  beforeEach(() => {
    jest.clearAllMocks();
    api.get.mockImplementation((path) => {
      if (path.startsWith("/cards/")) return Promise.resolve({ data: typicalCharacter });
      return Promise.resolve({ data: { records: [] } });
    });
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  const renderSheet = async (card) => {
    api.get.mockImplementation((path) => {
      if (path.startsWith("/cards/")) return Promise.resolve({ data: card });
      return Promise.resolve({ data: { records: [] } });
    });

    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={[`/carta/${card.id}/scheda`]}>
          <Routes>
            <Route path="/carta/:id/scheda" element={<CharacterSheet />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });
  };

  it.each([
    ["empty", emptyCharacter],
    ["typical", typicalCharacter],
    ["rich", richCharacter],
  ])("keeps both printable A4 faces available for a %s character", async (_scenario, card) => {
    await renderSheet(card);

    expect(container.querySelector('[data-testid="character-sheet"]')).not.toBeNull();
    expect(container.querySelectorAll(".tf-sheet-a4")).toHaveLength(2);
    expect(container.querySelectorAll(".tf-print-columns")).toHaveLength(2);
    expect(container.querySelectorAll(".tf-print-abilities")).toHaveLength(1);
    expect(container.querySelector('[data-testid="print-character-sheet"]')).not.toBeNull();
  });

  it("keeps the last rich spell and equipment entry in the document instead of clipping the lists", async () => {
    await renderSheet(richCharacter);

    expect(container.textContent).toContain("Incantesimo di prova 18");
    expect(container.textContent).toContain("Equipaggiamento di prova 18");
    expect(container.textContent).toContain("Arco-lungo-con-un-identificatore-molto-lungo-senza-spazi");
    expect(container.querySelectorAll(".tf-wrap-anywhere").length).toBeGreaterThan(0);

    const faces = container.querySelectorAll(".tf-sheet-a4");
    const sectionsAfterBack = [];
    for (let sibling = faces[1].nextElementSibling; sibling; sibling = sibling.nextElementSibling) {
      if (sibling.tagName === "SECTION") sectionsAfterBack.push(sibling);
    }
    expect(sectionsAfterBack).not.toHaveLength(0);
    expect(sectionsAfterBack.every((section) => section.classList.contains("no-print"))).toBe(true);
  });

  it("locks the native print layout to a marginless two-face A4 geometry", () => {
    const css = readFileSync(resolve(process.cwd(), "src/index.css"), "utf8");

    expect(css).toMatch(/@page\s*\{[\s\S]*size:\s*A4 portrait;[\s\S]*margin:\s*0;/);
    expect(css).toMatch(/body\s*\{\s*margin:\s*0 !important;/);
    expect(css).toMatch(/\.character-sheet-page \.tf-sheet-a4\s*\{[\s\S]*width:\s*210mm !important;[\s\S]*min-height:\s*297mm;[\s\S]*margin:\s*0 !important;/);
    expect(css).toMatch(/\[data-testid="character-sheet"\]\s*\{[\s\S]*width:\s*210mm !important;[\s\S]*max-width:\s*none !important;/);
    expect(css).toMatch(/\.tf-print-abilities\s*\{[\s\S]*repeat\(6, minmax\(0, 1fr\)\) !important;/);
    expect(css).toMatch(/\.tf-print-front-columns\s*\{[\s\S]*minmax\(0, 1\.1fr\) minmax\(0, \.9fr\) !important;/);
    expect(css).toMatch(/\.tf-print-back-columns\s*\{[\s\S]*minmax\(0, 1\.15fr\) minmax\(0, \.85fr\) !important;/);
  });
});