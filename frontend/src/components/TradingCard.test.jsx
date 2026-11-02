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

describe("reference card statistics medallions", () => {
  it("uses the approved CA and PF icons without substituting symbols for other statistics", async () => {
    const element = document.createElement("div");
    document.body.appendChild(element);
    const root = createRoot(element);
    await act(async () => {
      root.render(<CardFront card={{
        type:"monster",name:"Drago Rosso Adulto",
        attributes:{classe_armatura:"19",punti_ferita:"256",velocita:"12 m"}
      }}/>);
    });
    const badges = [...element.querySelectorAll(".tf-v6-stat-icon")];
    expect(badges.map(img=>img.getAttribute("src")))
      .toEqual(["/card-art/stat-ca-clean-v24.svg","/card-art/stat-pf-clean-v24.svg"]);
    const integratedRows=[...element.querySelectorAll(".tf-v6-stat-value-row")];
    expect(integratedRows).toHaveLength(2);
    expect(integratedRows.map(row=>[row.querySelector("img")?.getAttribute("src"),row.querySelector("strong")?.textContent]))
      .toEqual([["/card-art/stat-ca-clean-v24.svg","19"],["/card-art/stat-pf-clean-v24.svg","256"]]);
    expect(element.querySelectorAll(".tf-v3-stat > .tf-v6-stat-icon")).toHaveLength(0);
    expect(element.querySelectorAll(".tf-v3-stat")).toHaveLength(3);
    expect([...element.querySelectorAll("[data-stat-label]")].map(el=>el.getAttribute("data-stat-label")))
      .toEqual(["CA","PF","Vel."]);
    await act(async () => root.unmount());
    element.remove();
  });
});
describe("approved class preview",()=>{
 it("shows one ruby d10 and exact beginning of original paragraph, with no heading",async()=>{
   const mount=document.createElement("div");document.body.appendChild(mount);
   const root=createRoot(mount);
   await act(async()=>root.render(<CardFront card={{type:"class",name:"Guerriero",
     attributes:{dado_vita:"d10",abilita_primaria:"Forza o Destrezza",
       tiri_salvezza:"Forza, Costituzione",
       _legacy_full_text_before_20261024:"Un’umana in una sferragliante corazza di piastre"}}}/>));
   expect(mount.querySelector('[data-front-category="class"]')).not.toBeNull();
   expect(mount.querySelector(".tf-v7-description-label")).toBeNull();
   expect(mount.querySelector(".tf-v3-class-dice")?.textContent).toBe("d10");
   expect(mount.querySelector(".tf-v3-class-dice")?.style.backgroundImage).toContain("/class-dice/d10-premium-v29.webp");
   expect(mount.querySelector(".tf-v3-desc")?.textContent).toContain("Un’umana");
   expect([...mount.querySelectorAll(".tf-v3-stat")].map(el=>el.dataset.statLabel)).not.toContain("Dado vita");
   await act(async()=>root.unmount());mount.remove();
 });
});
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

describe("new front integration",()=>{
 it("renders vector filigree without a pasted reference label",async()=>{
   const container=document.createElement("div");
   document.body.appendChild(container);
   const root=createRoot(container);
   await act(async()=>root.render(<CardFront card={{type:"monster",name:"Drago Rosso Adulto",attributes:{tipo_creatura:"Drago",grado_sfida:"17"}}}/>));
   const front=container.querySelector('[data-front-layout="reference-master-v17"]');
   expect(front).not.toBeNull();
   expect(front.querySelector(".tf-v5-bottom-rail")).toBeNull();
   expect(front.querySelectorAll(".tf-v4-filigree")).toHaveLength(0);
   expect(front.querySelector("[data-front-detail-repair]")).toBeNull();
   expect(front.querySelector("img").getAttribute("alt")).toBe("Drago Rosso Adulto");
   await act(async()=>root.unmount());
   container.remove();
 });
});

describe("v10: approved dragon high resolution and readable senses",()=>{
  it("uses an original-size separate Dragon medal and preserves all senses",async()=>{
    const container=document.createElement("div");document.body.appendChild(container);
    const root=createRoot(container);
    await act(async()=>root.render(<CardFront card={{type:"monster",name:"Drago Rosso Adulto",
      attributes:{tipo_creatura:"Drago",grado_sfida:"17",sensi:"Percezione passiva 23, scurovisione 36 m, vista cieca 18 m"}}}/>));
    const emblem=container.querySelector(".tf-v3-sprite");
    expect(emblem.style.backgroundImage).toContain("drago-originale-hd-v2.webp");
    expect(emblem.style.backgroundSize).toBe("100% 100%");
    expect(container.querySelector('[data-testid="front-emblem"]').dataset.emblemSprite).toBe("drago-hd");
    expect(container.querySelector("[data-front-layout]")?.className).toContain("tf-v6-long-title");
    expect(container.textContent).toContain("vista cieca 18 m");
    await act(async()=>root.unmount());container.remove();
  });
});

// A spell has the same PREMIUM jewel as its class counterpart, but with an
// explicit full damage formula (8d6 is never reduced to d6 in the description).
describe("approved premium spell dice",()=>{
  it("renders fireball with a d6 jewel, complete 8d6 and no class dice badge",async()=>{
    const mount=document.createElement("div");document.body.appendChild(mount);
    const root=createRoot(mount);
    await act(async()=>root.render(<CardFront card={{type:"spell",name:"Palla di Fuoco",attributes:{
      livello:"3",scuola:"Invocazione",danno:"8d6 fuoco"
    }}}/>));
    expect(mount.querySelector('[data-front-category="spell"]')).not.toBeNull();
    expect(mount.querySelector('.tf-v3-spell-dice img')?.getAttribute("src"))
      .toBe("/card-art/spell-dice/d6-blank-v31.webp");
    expect(mount.querySelector(".tf-v3-spell-formula")?.textContent).toBe("8d6");
    expect(mount.querySelector(".tf-v3-spell-dice")?.textContent).toBe("8d6");
    expect(mount.querySelector(".tf-v3-spell-formula")?.style.fontSize).toBe("21px");
    expect(mount.querySelector(".tf-v3-class-dice")).toBeNull();
    await act(async()=>root.unmount());mount.remove();
  });
  it("does not create a fake medallion for a non-damaging spell",async()=>{
    const mount=document.createElement("div");document.body.appendChild(mount);
    const root=createRoot(mount);
    await act(async()=>root.render(<CardFront card={{type:"spell",name:"Scudo",attributes:{scuola:"Abiurazione"}}}/>));
    expect(mount.querySelector(".tf-v3-spell-dice")).toBeNull();
    await act(async()=>root.unmount());mount.remove();
  });
});

describe("final Class row and crisp Guerriero medal",()=>{
 it("keeps three independently labelled stat cells with crisp image icons",async()=>{
   const mount=document.createElement("div");document.body.appendChild(mount);
   const root=createRoot(mount);
   await act(async()=>root.render(<CardFront card={{type:"class",name:"Guerriero",attributes:{
     abilita_primaria:"Forza o Destrezza",tiri_salvezza:"Forza, Costituzione",
     competenze:"Tutte le armature, scudi, armi semplici e da guerra",dado_vita:"d10"
   },description:"Una frase completa. Una seconda frase completa."}}/>));
   const cells=[...mount.querySelectorAll(".tf-v3-class-stat")];
   expect(mount.querySelector(".tf-v39-class-master")?.getAttribute("src"))
     .toBe("/card-art/class-master-reference-v39.webp");
   expect(cells).toHaveLength(3);
   expect(cells.map(c=>c.querySelector("img").getAttribute("src")))
     .toEqual(["/card-art/class-stats/primary-v33.svg","/card-art/class-stats/saves-v33.svg","/card-art/class-stats/proficiencies-v33.svg"]);
   expect(mount.querySelector(".tf-v3-sprite").style.backgroundImage)
     .toContain("/card-art/guerriero-approved-medal-v39.webp");
   expect(mount.querySelector(".tf-v3-desc").textContent).toBe("Una frase completa. Una seconda frase completa.");
   await act(async()=>root.unmount());mount.remove();
 });
});
