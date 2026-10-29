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
      expect(data.dice).toBe("1d8+2");
    }
  );
  it("ignores previous color, foil, motto and custom front style settings", () => {
    const card={type:"spell",name:"Prova",attributes:{scuola:"Invocazione"}};
    expect(buildFrontBlueprint({...card, appearance:{title_effect:"rainbow",front_background_start:"#f00"}}))
      .toEqual(buildFrontBlueprint(card));
  });
});
