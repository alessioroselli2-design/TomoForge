import { buildFrontBlueprint } from "./cardFrontBlueprint";

describe("TomoForge v2 front blueprint", () => {
  it("does not invent monster data, preserving the source values and six abilities", () => {
    const data = buildFrontBlueprint({ type: "monster", name: "Drago", attributes: {
      tipo_creatura: "Drago", classe_armatura: "17", punti_ferita: "120",
      velocita: "9 m", for: "18", des: "14", cos: "16", int: "12", sag: "10", car: "8", danno: "2d8+4",
    }});
    expect(data.heading).toBe("MOSTRO");
    expect(data.crest).toBe("D");
    expect(data.highlights.map(s=>s.value)).toEqual(["17","120","9 m"]);
    expect(data.abilities).toHaveLength(6);
    expect(data.dice).toBe("2d8+4");
  });
  it("uses spell school and real spell dice, not monster stats", () => {
    const data = buildFrontBlueprint({type:"spell",name:"Palla di Fuoco", attributes:{
      livello:"3", scuola:"Invocazione", tempo_lancio:"1 azione", gittata:"45 m", danno:"8d6 fuoco"
    }});
    expect(data.subtitle).toBe("Invocazione");
    expect(data.abilities).toHaveLength(0);
    expect(data.dice).toBe("8d6");
    expect(data.spellDie).toBe("d6");
    expect(data.spellDieAsset).toBe("/card-art/spell-dice/d6-blank-v31.webp");
    expect(data.highlights).toHaveLength(3);
  });
  it("displays no invented formula or empty stats on a placeholder card", () => {
    const data = buildFrontBlueprint({type:"monster",name:"Senza dati",attributes:{}});
    expect(data.dice).toBe("");
    expect(data.highlights).toHaveLength(0);
    expect(data.abilities).toHaveLength(0);
  });
  it.each(["class","subclass","feature","race","feat","weapon","armor","item","character","custom"])(
    "provides a bounded layout for category %s", type => {
      const data = buildFrontBlueprint({type, name:"Prova", attributes:{livello:"5",danno:"1d8+2"}});
      expect(data.heading).toBeTruthy();
      expect(data.highlights.length).toBeLessThanOrEqual(3);
      expect(data.details.length).toBeLessThanOrEqual(3);
      expect(data.dice).toBe(type === "class" ? "" : "1d8+2");
    }
  );
  it("ignores previous color, foil, motto and custom front style settings", () => {
    const card={type:"spell",name:"Prova",attributes:{scuola:"Invocazione"}};
    expect(buildFrontBlueprint({...card, appearance:{title_effect:"rainbow",front_background_start:"#f00"}}))
      .toEqual(buildFrontBlueprint(card));
  });
});

describe("approved upper cartouche",()=>{
  it("shows creature type, size and alignment, with GS in badge only",()=>{
    const data=buildFrontBlueprint({type:"monster",name:"Drago Rosso Adulto",attributes:{
      tipo_creatura:"Drago",taglia:"Enorme",allineamento:"Caotico Malvagio",grado_sfida:"17"
    }});
    expect(data.subtitle).toBe("Drago • Enorme • Caotico Malvagio");
    expect(data.badge).toEqual({top:"GS",value:"17"});
  });
  it("uses school and class without duplicating spell level",()=>{
    const data=buildFrontBlueprint({type:"spell",name:"Palla di Fuoco",attributes:{
      classe:"Mago",scuola:"Invocazione",livello:"3"
    }});
    expect(data.subtitle).toBe("Mago • Invocazione");
    expect(data.badge.value).toBe("3");
    expect(data.subtitle).not.toContain("livello");
  });
  it("shows a character's subclass and a feature's parent class",()=>{
    expect(buildFrontBlueprint({type:"character",attributes:{classe:"Druido",sottoclasse:"Circolo delle Stelle"}}).subtitle)
      .toBe("Druido • Circolo delle Stelle");
    expect(buildFrontBlueprint({type:"feature",attributes:{classe:"Druido"}}).subtitle)
      .toBe("Druido • Privilegio di Classe");
  });
  it("retains simple race label and omits repeated level",()=>{
    expect(buildFrontBlueprint({type:"race",name:"Elfo"}).subtitle).toBe("Razza");
  });
});

describe("approved reference details",()=>{
  it("adds D&D modifiers to raw score without modifying the source record",()=>{
    const attrs={for:"27",des:"10",cos:"25",int:"16",sag:"13",car:"21"};
    const card={type:"monster",name:"Drago Rosso Adulto",attributes:attrs};
    const values=buildFrontBlueprint(card).abilities.map(e=>e.value);
    expect(values).toEqual(["27 (+8)","10 (+0)","25 (+7)","16 (+3)","13 (+1)","21 (+5)"]);
    expect(attrs.for).toBe("27");
  });
  it("uses resistance, senses and actions rather than repeating GS and creature type",()=>{
    const bp=buildFrontBlueprint({type:"monster",name:"Drago",attributes:{
      grado_sfida:"17",tipo_creatura:"Drago",resistenze:"Fuoco",sensi:"Scurovisione 36 m",azioni:["Morso","Artigli"]
    }});
    expect(bp.details.map(d=>d.key)).toEqual(["resistenze","sensi","azioni"]);
    expect(bp.details[2].value).toBe("Morso · Artigli");
    expect(bp.badge.value).toBe("17");
  });
});

describe("movement-mode presentation",()=>{
 it("does not chop a monster's flying or climbing speed after nineteen characters",()=>{
   const card={type:"monster",name:"Drago Rosso Adulto",attributes:{
     velocita:"12 m, scalare 12 m, volare 36 m",
     tipo_creatura:"Drago",grado_sfida:"17"
   }};
   const speed=buildFrontBlueprint(card).highlights.find(item=>item.label==="Vel.");
   expect(speed.value).toContain("scal. 12 m");
   expect(speed.value).toContain("vol. 36 m");
   expect(speed.value).not.toContain("…");
   expect(speed.fullValue).toContain("volare 36 m");
 });
});

describe("approved class: source-faithful narrative with d10",()=>{
 it("preserves exact legacy text, without repetitive Dado vita heading",()=>{
   const original="Un’umana in una sferragliante corazza di piastre solleva lo scudo davanti a sé.";
   const card={type:"class",name:"Guerriero",
     description:"Guerriero — Dado Vita d10. Tiri salvezza: Forza, Costituzione. Competenza in tutte le armature, scudi, armi semplici e marziali.",
     attributes:{dado_vita:"d10",abilita_primaria:"Forza o Destrezza",
       tiri_salvezza:"Forza, Costituzione",_legacy_full_text_before_20261024:original}};
   const data=buildFrontBlueprint(card);
   expect(data.highlights.map(x=>x.label)).toEqual(["Abilità primaria","Tiri salvezza","Competenze"]);
   expect(data.highlights[2].value).toContain("tutte le armature");
   expect(data.dice).toBe("d10");
   expect(data.showDescriptionLabel).toBe(false);
   expect(data.description).toBe(original);
   expect(card.description).toContain("Dado Vita d10");
 });
 it("does not introduce fictitious class narrative when no legacy source exists",()=>{
   const data=buildFrontBlueprint({type:"class",name:"Bardo",description:"Testo già disponibile.",attributes:{dado_vita:"d8"}});
   expect(data.description).toBe("Testo già disponibile.");
   expect(data.dice).toBe("d8");
   expect(data.highlights).toHaveLength(0);
 });
});

describe("v27: one ornate die silhouette for each verified Hit Die",()=>{
  it.each([
    ["Mago","d6"],["Stregone","d6"],["Druido","d8"],["Bardo","d8"],
    ["Guerriero","d10"],["Paladino","d10"],["Barbaro","d12"],
    ["Personalizzato","d4"],["Epico","d20"],
  ])("%s uses its stored die %s",(name,die)=>{
    const bp=buildFrontBlueprint({type:"class",name,attributes:{dado_vita:die}});
    expect(bp.dice).toBe(die);
    expect(bp.classDieAsset).toBe(`/card-art/class-dice/${die}-premium-v29.webp`);
  });
  it("does not guess a die from a class name or its damage",()=>{
    const bp=buildFrontBlueprint({type:"class",name:"Barbaro",attributes:{danno:"2d12"}});
    expect(bp.dice).toBe(""); expect(bp.classDieAsset).toBe("");
  });
  it("normalizes valid dice strings supplied by different imports",()=>{
    expect(buildFrontBlueprint({type:"class",attributes:{dado_vita:"1D 8"}}).dice).toBe("d8");
  });
  it("ends the authentic card excerpt with a visible ellipsis and preserves full source",()=>{
    const whole=("Un’umana in una sferragliante corazza di piastre solleva lo scudo davanti a sé. ").repeat(12);
    const bp=buildFrontBlueprint({type:"class",attributes:{_legacy_full_text_before_20261024:whole}});
    expect(bp.description.endsWith("…")).toBe(true);
    expect(bp.description.length).toBeLessThanOrEqual(290);
    expect(bp.classLegacyText).toBe(whole.trim());
  });
});

// The spell's full damage formula stays dynamic, but the artwork matches its die.
describe("spell damage jewel mapping",()=>{
  it.each([["1d4","d4"],["8d6","d6"],["3d8+2","d8"],["2d10+3","d10"],["1d12","d12"],["1d20","d20"]])(
    "renders %s with the approved %s visual master", (formula,die)=>{
      const bp=buildFrontBlueprint({type:"spell",attributes:{danno:formula+" fuoco"}});
      expect(bp.dice).toBe(formula);
      expect(bp.spellDie).toBe(die);
      const version = ["d12","d20"].includes(die) ? "clean-v32" : "blank-v31";
      expect(bp.spellDieAsset).toBe(`/card-art/spell-dice/${die}-${version}.webp`);
    });
  it("does not invent jewel for spells without damage or unsupported dice",()=>{
    expect(buildFrontBlueprint({type:"spell",attributes:{scuola:"Abiurazione"}}).spellDieAsset).toBe("");
    expect(buildFrontBlueprint({type:"spell",attributes:{danno:"1d100"}}).spellDieAsset).toBe("");
    expect(buildFrontBlueprint({type:"class",attributes:{dado_vita:"d10"}}).spellDieAsset).toBe("");
  });
});

describe("clean d12 and d20 spell artworks",()=>{
  it.each(["d12","d20"])("loads an unlettered %s v32 jewel without modifying class art",die=>{
    const fs=require("fs");
    const path=require("path");
    const bp=buildFrontBlueprint({type:"spell",name:"Prova",attributes:{danno:`1${die}`}});
    expect(bp.spellDieAsset).toBe(`/card-art/spell-dice/${die}-clean-v32.webp`);
    const disk=fs.readFileSync(path.resolve(__dirname,`../../public/card-art/spell-dice/${die}-clean-v32.webp`));
    expect(disk.subarray(0,4).toString()).toBe("RIFF");
    expect(disk.subarray(8,12).toString()).toBe("WEBP");
    const klass=buildFrontBlueprint({type:"class",attributes:{dado_vita:die}});
    expect(klass.classDieAsset).toBe(`/card-art/class-dice/${die}-premium-v29.webp`);
  });
});
