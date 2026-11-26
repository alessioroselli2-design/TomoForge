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
   expect(mount.querySelector(".tf-class-hit-die")?.textContent).toBe("d10");
   expect(mount.querySelector(".tf-class-hit-die")?.style.backgroundImage).toContain("/dadi-vita/d10.png");
   expect(mount.querySelector(".tf-v3-desc")?.textContent).toContain("Un’umana");
   expect([...mount.querySelectorAll(".tf-v3-stat")].map(el=>el.dataset.statLabel)).not.toContain("Dado vita");
   await act(async()=>root.unmount());mount.remove();
 });
});
describe("class dice and original ability PNGs: four regression samples",()=>{
 test.each([
   ["Guerriero","Forza o Destrezza","d10",["forza","destrezza"]],
   ["Mago","Intelligenza","d6",["intelligenza"]],
   ["Paladino","Forza e Carisma","d10",["forza","carisma"]],
   ["Ranger","Destrezza e Saggezza","d10",["destrezza","saggezza"]],
   ["Bardo","Carisma","d8",["carisma"]],
   ["Barbaro","Forza","d12",["forza"]],
 ])("%s uses %s and %s",async(name,ability,die,icons)=>{
   const mount=document.createElement("div");document.body.appendChild(mount);
   const root=createRoot(mount);
   await act(async()=>root.render(<CardFront card={{
     type:"class",name,attributes:{dado_vita:die,abilita_primaria:ability}
   }}/>));
   const card=mount.querySelector('[data-front-category="class"]');
   expect(card).not.toBeNull();
   const primary=card.querySelector('[data-stat-label="Abilità primaria"]');
   expect([...primary.querySelectorAll(".tf-class-primary-icons img")].map(x=>x.getAttribute("src")))
     .toEqual(icons.map(x=>`/icone-caratteristiche/${x}.png`));
   expect(primary.querySelector(".tf-class-primary-double")!==null).toBe(icons.length===2);
   expect(primary.querySelector(".tf-class-primary-row strong")?.textContent).toBe(ability);
   expect(card.querySelector(".tf-class-hit-die")?.style.backgroundImage)
     .toContain(`/dadi-vita/${die}.png`);
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
    const card = { id: "c1", type: "custom", name: "Magia Oscura", artwork_path: null };
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
    const card = { id: "c2", type: "custom", name: "Incantesimo" };
    await act(async () => {
      root.render(<CardFront card={card} exportMode />);
    });
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img.src).toContain("artwork-placeholder.svg");
  });

  it("does NOT show the editor hint overlay in exportMode even when artwork is absent", async () => {
    const card = { id: "c3", type: "custom", name: "Ombra Silenziosa", artwork_path: null };
    await act(async () => {
      root.render(<CardFront card={card} exportMode />);
    });
    // The "GENERA ARTWORK" editor-mode hint must not appear in the exported image.
    expect(container.textContent).not.toContain("GENERA ARTWORK");
  });

  it("uses the artworkUrl helper when artwork_path is provided", async () => {
    const card = { id: "c4", type: "custom", name: "Raggio Ardente", artwork_path: "uploads/spell.jpg" };
    await act(async () => {
      root.render(<CardFront card={card} exportMode />);
    });
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img.src).toContain("uploads/spell.jpg");
    expect(img.src).not.toContain("artwork-placeholder.svg");
  });

  it("does not loop if the artwork placeholder also fails to load", async () => {
    const card = { id: "c5", type: "custom", name: "Eco Spezzata", artwork_path: "uploads/spell.jpg" };
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
    const card = { id: "c7", type: "custom", name: "Segnale Perduto", artwork_path: "uploads/broken.jpg" };
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
    const card = { id: "c8", type: "custom", name: "Faglia Silenziosa", artwork_path: "uploads/broken.jpg" };
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
    const card = { id: "c6", type: "custom", name: "Rinascita", artwork_path: "uploads/broken.jpg" };
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
   const front=container.querySelector('[data-front-layout="unified-monster-master-v17"]');
   expect(front).not.toBeNull();
   expect(front.querySelector(".tf-v5-bottom-rail")).toBeNull();
   expect(front.querySelectorAll(".tf-v4-filigree")).toHaveLength(0);
   expect(front.querySelector("[data-front-detail-repair]")).toBeNull();
   expect(front.querySelector("img").getAttribute("alt")).toBe("Drago Rosso Adulto");
   await act(async()=>root.unmount());
   container.remove();
 });
});

describe("Monster full PNG emblem selection",()=>{
  it("switches all fourteen creature types and shows no fallback for unknown types",async()=>{
    const container=document.createElement("div");document.body.appendChild(container);
    const root=createRoot(container);
    const types=["aberrazione","bestia","celestiale","costrutto","drago","elementale","folletto","gigante","immondo","melma","mostruosita","non morto","pianta","umanoide"];
    try {
      for (const [index,type] of types.entries()) {
        await act(async()=>root.render(<CardFront card={{type:"monster",name:"Mostro",attributes:{tipo_creatura:type}}}/>));
        const emblem=container.querySelector('[data-testid="front-emblem"]');
        expect(emblem.getAttribute("src")).toBe("/emblemi/mostri/mst-"+String(index+1).padStart(2,"0")+"-"+type.replace(/ /g,"-")+".png");
        expect(emblem.style.width).toBe("26.5%");
        expect(container.querySelector(".tf-v3-sprite, .tf-v3-medallion")).toBeNull();
      }
      await act(async()=>root.render(<CardFront card={{type:"monster",name:"Mostro",attributes:{tipo_creatura:"sconosciuto"}}}/>));
      expect(container.querySelector('[data-testid="front-emblem"]')).toBeNull();
    } finally {await act(async()=>root.unmount());container.remove();}
  });
});

describe("v10: approved dragon high resolution and readable senses",()=>{
  it("uses an original-size separate Dragon medal and preserves all senses",async()=>{
    const container=document.createElement("div");document.body.appendChild(container);
    const root=createRoot(container);
    await act(async()=>root.render(<CardFront card={{type:"monster",name:"Drago Rosso Adulto",
      attributes:{tipo_creatura:"Drago",grado_sfida:"17",sensi:"Percezione passiva 23, scurovisione 36 m, vista cieca 18 m"}}}/>));
    const emblem=container.querySelector('[data-testid="front-emblem"]');
    expect(emblem.tagName).toBe("IMG");
    expect(emblem.getAttribute("src")).toBe("/emblemi/mostri/mst-05-drago.png");
    expect(emblem.dataset.emblemSprite).toBe("monster-original");
    expect(emblem.style.width).toBe("26.5%");
    expect(container.querySelector(".tf-v3-sprite, .tf-v3-medallion")).toBeNull();
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
    expect(mount.querySelector('.tf-spell-damage img')?.getAttribute("src"))
      .toBe("/card-art/spell-dice/d6-blank-v31.webp");
    expect(mount.querySelector(".tf-spell-damage strong")?.textContent).toBe("8d6");
    expect(mount.querySelector(".tf-spell-damage")?.textContent).toBe("8d6");
    expect(mount.querySelector(".tf-spell-school-emblem")?.getAttribute("src")).toBe("/emblemi/scuole/scl-06-invocazione.png");
    expect(mount.querySelector(".tf-class-hit-die")).toBeNull();
    await act(async()=>root.unmount());mount.remove();
  });
  it("does not create a fake medallion for a non-damaging spell",async()=>{
    const mount=document.createElement("div");document.body.appendChild(mount);
    const root=createRoot(mount);
    await act(async()=>root.render(<CardFront card={{type:"spell",name:"Scudo",attributes:{scuola:"Abiurazione"}}}/>));
    expect(mount.querySelector(".tf-spell-damage")).toBeNull();
    await act(async()=>root.unmount());mount.remove();
  });
});

describe("One Monster master for all cards, with category-specific data",()=>{
 const mountCard=async card=>{
   const mount=document.createElement("div");document.body.appendChild(mount);
   const root=createRoot(mount);
   await act(async()=>root.render(<CardFront card={card}/>));
   return {mount,root,close:async()=>{await act(async()=>root.unmount());mount.remove()}};
 };
 it("keeps the Monster unchanged and uses the SAME raster for the Warrior",async()=>{
   const monster=await mountCard({type:"monster",name:"Drago",attributes:{
     classe_armatura:"18",punti_ferita:"200",grado_sfida:"14"}});
   const warrior=await mountCard({type:"class",name:"Guerriero",attributes:{
     abilita_primaria:"Forza o Destrezza",tiri_salvezza:"Forza, Costituzione",
     competenze:"Tutte le armature, scudi, armi semplici e da guerra",dado_vita:"d10"
   },description:"Una frase completa. Una seconda frase completa."});
   const m=monster.mount.querySelector("[data-testid='card-front']");
   const c=warrior.mount.querySelector("[data-testid='card-front']");
   expect(c.dataset.frontVersion).toBe("7");
   expect(m.dataset.frontLayout).toBe("unified-monster-master-v17");
   expect(c.dataset.frontLayout).toBe(m.dataset.frontLayout);
   expect(c.dataset.categoryLayout).toBe("class-5x7-finale");
   expect(c.style.backgroundImage).toContain("/card-art/master-classe-5x7-senza-muscolo-e-anello-20261118.jpg");
   expect(c.style.backgroundImage).not.toBe(m.style.backgroundImage);
   expect(c.style.backgroundImage).toContain("/card-art/master-classe-5x7-senza-muscolo-e-anello-20261118.jpg");
   expect(c.querySelectorAll(".tf-v3-layout")).toHaveLength(1);
   expect(c.querySelectorAll(".tf-class-v40-master,.tf-v39-class-master")).toHaveLength(0);
   expect([...c.querySelectorAll(".tf-v3-stat")].map(el=>el.dataset.statLabel))
     .toEqual(["Abilità primaria","Tiri salvezza","Competenze"]);
   expect(c.querySelector('[data-stat-label="Competenze"]').title)
     .toBe("Tutte le armature, scudi, armi semplici e da guerra");
   expect(c.querySelector(".tf-class-hit-die").style.backgroundImage).toContain("d10.png");
   expect(c.querySelector(".tf-v3-desc").textContent)
     .toBe("Una frase completa. Una seconda frase completa.");
   expect(c.querySelector(".tf-v3-details")).toBeNull();
   expect(c.dataset.categoryLayout).toBe("class-5x7-finale");
   expect(c.querySelector(".tf-v3-badge")).toBeNull();
   expect([...m.querySelectorAll(".tf-v3-badge")].map(x=>x.textContent)).toEqual(["GS14"]);
   await warrior.close();await monster.close();
 });
 it("leaves the Class artwork window empty until a real image is provided",async()=>{
   const card={type:"class",name:"Guerriero",attributes:{dado_vita:"d10"}};
   const {mount,root,close}=await mountCard(card);
   expect(mount.querySelector("[data-testid='front-artwork-empty']")).not.toBeNull();
   expect(mount.querySelector(".tf-v3-picture img")).toBeNull();
   expect(mount.querySelector(".tf-v3-picture img")).toBeNull();
   await act(async()=>root.render(<CardFront card={card} imgUrl="data:image/png;base64,ZGF0YQ=="/>));
   expect(mount.querySelector(".tf-v3-picture img").getAttribute("src"))
     .toBe("data:image/png;base64,ZGF0YQ==");
   expect(mount.querySelector("[data-testid='front-artwork-empty']")).toBeNull();
   await close();
 });
 it("changes the Class emblem, die and information without changing the raster",async()=>{
   const {mount,close}=await mountCard({type:"class",name:"Druido",
     artwork_path:"druid.jpg",attributes:{dado_vita:"d8",abilita_primaria:"Saggezza"}});
   const c=mount.querySelector("[data-testid='card-front']");
   expect(c.style.backgroundImage).toContain("/card-art/master-classe-5x7-senza-muscolo-e-anello-20261118.jpg");
   expect(c.querySelector(".tf-v3-picture img").getAttribute("src"))
     .toBe("https://cdn.example.com/druid.jpg");
   expect(c.querySelector(".tf-v3-medallion")).not.toBeNull();
   expect(c.querySelector(".tf-class-hit-die").style.backgroundImage).toContain("d8.png");
   await close();
 });
 it("uses the approved Spell master while preserving the Magic Item master",async()=>{
   const spell=await mountCard({type:"spell",name:"Palla di Fuoco",attributes:{livello:"3",scuola:"Invocazione"}});
   const item=await mountCard({type:"item",name:"Anello",attributes:{rarita:"Raro"}});
   const approved=spell.mount.querySelector("[data-testid='card-front']");
   expect(approved.dataset.frontLayout).toBe("spell-5x7-v1");
   expect(approved.style.backgroundImage).toContain("/card-art/master-incantesimo-5x7-v1.webp");
   expect(approved.querySelector(".tf-spell-level")?.textContent).toContain("3");
   expect(approved.querySelector(".tf-spell-school-emblem")?.getAttribute("src"))
     .toBe("/emblemi/scuole/scl-06-invocazione.png");
   expect(item.mount.querySelector("[data-testid='card-front']").style.backgroundImage).toContain("master-oggetto-magico-5x7.png");
   expect(item.mount.querySelector(".tf-category-badge").textContent).toBe("Raro");
   await spell.close();await item.close();
 });
});

describe("Class primary ability PNGs do not overlap master symbols",()=>{
  const mountClass=async (name,primary)=>{
    const mount=document.createElement("div");document.body.appendChild(mount);
    const root=createRoot(mount);
    await act(async()=>root.render(<CardFront card={{type:"class",name,
      attributes:{abilita_primaria:primary,tiri_salvezza:"Forza, Costituzione",
        competenze:"Armature, scudi e armi",dado_vita:"d10"}}}/>));
    return {mount,close:async()=>{await act(async()=>root.unmount());mount.remove();}};
  };
  it("Barbaro and Mago each render one correct icon",async()=>{
    for(const [name,primary,file] of [["Barbaro","Forza","forza.png"],["Mago","INTELLIGÉNZA","intelligenza.png"]]){
      const {mount,close}=await mountClass(name,primary);
      const icons=[...mount.querySelectorAll('[data-stat-label="Abilità primaria"] .tf-class-primary-icons img')];
      expect(icons).toHaveLength(1);
      expect(icons[0].getAttribute("src")).toBe("/icone-caratteristiche/"+file);
      expect(mount.querySelector('[data-stat-label="Tiri salvezza"] img')).toBeNull();
      expect(mount.querySelector('[data-stat-label="Competenze"] img')).toBeNull();
      expect(mount.querySelectorAll(".tf-class-hit-die")).toHaveLength(1);
      await close();
    }
  });
  it("Guerriero vertically stacks exactly two characteristic icons",async()=>{
    const {mount,close}=await mountClass("Guerriero","Forza o Destrezza");
    const row=mount.querySelector(".tf-class-primary-row");
    expect(row.classList.contains("tf-class-primary-double")).toBe(true);
    expect([...row.querySelectorAll("img")].map(x=>x.getAttribute("src")))
      .toEqual(["/icone-caratteristiche/forza.png","/icone-caratteristiche/destrezza.png"]);
    expect(row.querySelector("strong").textContent).toBe("Forza o Destrezza");
    expect(mount.querySelectorAll(".tf-v6-stat-icon")).toHaveLength(0);
    await close();
  });
});

describe("Class 5x7 uses the master image and clean emblems",()=>{
 it("uses a single master and has no illustration prompt on an empty Class",async()=>{
  const m=document.createElement("div");document.body.appendChild(m);const root=createRoot(m);
  await act(async()=>root.render(<CardFront editorMode card={{type:"class",name:"Mago",attributes:{
   dado_vita:"d6",abilita_primaria:"Intelligenza",tiri_salvezza:"Intelligenza, Saggezza",competenze:"Armi semplici"
  }}}/>));
  const front=m.querySelector('[data-front-category="class"]');
  expect(front.style.backgroundImage).toContain("master-classe-5x7-senza-muscolo-e-anello-20261118.jpg");
  expect(front.querySelector(".tf-v3-art-hint")).toBeNull();
  expect(front.querySelector("[data-testid='front-artwork-empty']")).not.toBeNull();
  expect(front.querySelector(".tf-class-original-emblem")?.getAttribute("src"))
   .toBe("/emblemi/classi/cls-12-mago.png");
  expect(front.querySelectorAll(".tf-v3-sprite")).toHaveLength(0);
  expect(front.querySelector('[data-stat-label="Abilità primaria"] .tf-v6-stat-text>span').textContent)
   .toBe("Abilità Primaria");
  expect(front.querySelectorAll('[data-stat-label="Abilità primaria"] .tf-class-primary-icons img')).toHaveLength(1);
  await act(async()=>root.unmount());m.remove();
 });
});

describe("approved Incantesimo integration", () => {
  it("uses the same school master in the editor, detail and export DOM", async () => {
    const mount=document.createElement("div");
    document.body.appendChild(mount);
    const root=createRoot(mount);
    await act(async () => root.render(<CardFront card={{
      type:"spell",name:"Scudo",attributes:{scuola:"Abiurazione",livello:"1"}
    }} editorMode />));
    const front=mount.querySelector('[data-front-category="spell"]');
    expect(front).not.toBeNull();
    expect(front.getAttribute("data-front-layout")).toBe("spell-5x7-v1");
    expect(front.querySelector(".tf-spell-school-emblem").getAttribute("src"))
      .toBe("/emblemi/scuole/scl-01-abiurazione.png");
    expect(front.querySelector(".tf-spell-school-medallion")).not.toBeNull();
    expect(front.querySelector(".tf-v3-medallion")).toBeNull();
    await act(async () => root.unmount());
    mount.remove();
  });
});

describe("subclass shares the approved class renderer",()=>{
 it("renders the real Class master and parent symbol, while keeping the subclass identity",async()=>{
  const host=document.createElement("div");document.body.appendChild(host);
  const root=createRoot(host);
  try{
   await act(async()=>root.render(<CardFront editorMode card={{type:"subclass",name:"Campione",description:"Descrizione specifica.",attributes:{parent_class:"Guerriero",dado_vita:"d10",abilita_primaria:"Forza",tiri_salvezza:"Forza, Costituzione",competenze:"Armature, scudi e armi"}}}/>));
   const node=host.querySelector('[data-record-category="subclass"]');
   expect(node.getAttribute("data-front-category")).toBe("class");
   expect(node.getAttribute("data-category-layout")).toBe("class-5x7-finale");
   expect(node.style.backgroundImage).toContain("master-classe-5x7-senza-muscolo-e-anello-20261118.jpg");
   expect(node.querySelector("h3").textContent).toBe("Campione");
   expect(node.querySelector(".tf-v3-titles p").textContent).toBe("Guerriero • Sottoclasse");
   expect(node.querySelector(".tf-class-original-emblem").getAttribute("src")).toBe("/emblemi/classi/cls-05-guerriero.png");
   expect(node.querySelector(".tf-class-hit-die").getAttribute("data-die")).toBe("d10");
   expect(node.querySelector('[data-testid="front-artwork-empty"]')).not.toBeNull();
   expect(node.querySelector(".tf-v3-desc").textContent).toBe("Descrizione specifica.");
   await act(async()=>root.render(<CardFront editorMode card={{type:"subclass",name:"",attributes:{}}}/>));
   expect(host.querySelector('[data-record-category="subclass"]')).not.toBeNull();
   expect(host.querySelector(".tf-class-original-emblem")).toBeNull();
   expect(host.querySelectorAll(".tf-v3-stat")).toHaveLength(3);
  }finally{await act(async()=>root.unmount());host.remove()}
 });
});
