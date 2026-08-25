import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { CardFront } from "./TradingCard";

global.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock("qrcode.react", () => ({
  QRCodeCanvas: () => null,
}));

jest.mock("lucide-react", () => ({
  Flame: () => null,
  Skull: () => null,
  Sword: () => null,
  Moon: () => null,
  Eye: () => null,
  Shield: () => null,
  Star: () => null,
  Sparkles: () => null,
}));

jest.mock("@/lib/api", () => ({
  artworkUrl: (path) => `https://cdn.example.com/${path}`,
}));

jest.mock("@/lib/cardTypes", () => ({
  typeLabel: () => "Magia",
  typeIcon: () => () => null,
  attrLabel: (k) => k.toUpperCase(),
  QUICK_FIELDS: {},
  DEFAULT_APPEARANCE: {},
  FRAME_STYLES: [{ id: "gold", colors: ["#f8d764", "#d4af37", "#c98b18"] }],
  TITLE_EFFECTS: [{ id: "gold", colors: ["#fffbd1", "#f8d764", "#c98b18"] }],
}));

jest.mock("@/lib/i18n", () => ({
  useI18n: () => ({ t: (k) => k }),
}));

describe("CardFront artwork placeholder", () => {
  let container;
  let root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  it("uses the SVG placeholder as img src when artwork_path is null", async () => {
    const card = { id: "c1", type: "spell", name: "Magia Oscura", artwork_path: null };
    await act(async () => {
      root.render(<CardFront card={card} exportMode />);
    });
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    // In the Jest file transform, the SVG import resolves to its basename string.
    // jsdom resolves that against the test origin, so src ends up containing the filename.
    expect(img.src).toContain("artwork-placeholder.svg");
  });

  it("uses the SVG placeholder as img src when artwork_path is undefined", async () => {
    const card = { id: "c2", type: "spell", name: "Incantesimo" };
    await act(async () => {
      root.render(<CardFront card={card} exportMode />);
    });
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img.src).toContain("artwork-placeholder.svg");
  });

  it("does NOT show the editor hint overlay in exportMode even when artwork is absent", async () => {
    const card = { id: "c3", type: "spell", name: "Ombra Silenziosa", artwork_path: null };
    await act(async () => {
      root.render(<CardFront card={card} exportMode />);
    });
    // The "GENERA ARTWORK" editor-mode hint must not appear in the exported image.
    expect(container.textContent).not.toContain("GENERA ARTWORK");
  });

  it("uses the artworkUrl helper when artwork_path is provided", async () => {
    const card = { id: "c4", type: "spell", name: "Raggio Ardente", artwork_path: "uploads/spell.jpg" };
    await act(async () => {
      root.render(<CardFront card={card} exportMode />);
    });
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img.src).toContain("uploads/spell.jpg");
    expect(img.src).not.toContain("artwork-placeholder.svg");
  });

  it("does not loop if the artwork placeholder also fails to load", async () => {
    const card = { id: "c5", type: "spell", name: "Eco Spezzata", artwork_path: "uploads/spell.jpg" };
    await act(async () => {
      root.render(<CardFront card={card} exportMode />);
    });
    const img = container.querySelector("img");
    expect(img).not.toBeNull();

    const srcSetter = jest.spyOn(HTMLImageElement.prototype, "src", "set");
    try {
      await act(async () => {
        img.dispatchEvent(new Event("error"));
      });
      const fallbackSrc = img.src;
      expect(fallbackSrc).toContain("artwork-placeholder.svg");
      expect(srcSetter).toHaveBeenCalledTimes(1);
      expect(srcSetter.mock.calls[0][0]).toContain("artwork-placeholder.svg");

      srcSetter.mockClear();
      await act(async () => {
        img.dispatchEvent(new Event("error"));
      });
      expect(srcSetter).not.toHaveBeenCalled();
      expect(img.src).toBe(fallbackSrc);
    } finally {
      srcSetter.mockRestore();
    }
  });

  it("exposes artwork failures as alerts without announcing the warning glyph", async () => {
    const card = { id: "c7", type: "spell", name: "Segnale Perduto", artwork_path: "uploads/broken.jpg" };
    await act(async () => {
      root.render(<CardFront card={card} editorMode imgUrl="https://cdn.example.com/broken.jpg" />);
    });

    const img = container.querySelector("img");
    await act(async () => {
      img.dispatchEvent(new Event("error"));
    });

    const alert = container.querySelector('[role="alert"]');
    expect(alert).not.toBeNull();
    expect(alert.textContent).toContain("Artwork non disponibile");
    const warningGlyph = alert.querySelector('[aria-hidden="true"]');
    expect(warningGlyph).not.toBeNull();
    expect(warningGlyph.textContent).toBe("⚠");
  });

  it("keeps artwork failure alerts out of exported cards while using the placeholder", async () => {
    const card = { id: "c8", type: "spell", name: "Faglia Silenziosa", artwork_path: "uploads/broken.jpg" };
    await act(async () => {
      root.render(<CardFront card={card} editorMode exportMode imgUrl="https://cdn.example.com/broken.jpg" />);
    });

    const img = container.querySelector("img");
    await act(async () => {
      img.dispatchEvent(new Event("error"));
    });

    expect(img.src).toContain("artwork-placeholder.svg");
    expect(container.querySelector('[role="alert"]')).toBeNull();
    expect(container.textContent).not.toContain("Artwork non disponibile");
  });

  it("resets the artwork fallback guard when a new image URL is assigned", async () => {
    const card = { id: "c6", type: "spell", name: "Rinascita", artwork_path: "uploads/broken.jpg" };
    await act(async () => {
      root.render(<CardFront card={card} editorMode imgUrl="https://cdn.example.com/broken.jpg" />);
    });

    const img = container.querySelector("img");
    await act(async () => {
      img.dispatchEvent(new Event("error"));
    });
    expect(container.textContent).toContain("Artwork non disponibile");

    await act(async () => {
      root.render(<CardFront card={card} editorMode imgUrl="https://cdn.example.com/fixed.jpg" />);
    });
    expect(container.textContent).not.toContain("Artwork non disponibile");
    expect(img.src).toContain("fixed.jpg");

    await act(async () => {
      img.dispatchEvent(new Event("error"));
    });
    expect(container.textContent).toContain("Artwork non disponibile");
  });
});
