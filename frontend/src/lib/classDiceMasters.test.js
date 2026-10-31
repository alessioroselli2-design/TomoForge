import {readFileSync} from "fs";
import {resolve} from "path";
import {CLASS_HIT_DICE,classHitDieAsset,normalizeClassHitDie} from "./classHitDice";

const masterPath=die=>resolve(__dirname,`../../public/card-art/class-dice/${die}-master-v28.svg`);
describe("single illustrated master family for every hit die",()=>{
  it.each(["d4","d6","d8","d10","d12","d20"])("ships the complete, self-contained %s ornate graphic",die=>{
    const svg=readFileSync(masterPath(die),"utf8");
    expect(svg).toContain('viewBox="0 0 256 256"');
    expect(svg).toContain('width="1024" height="1024"');
    expect(svg).toContain("Single approved ornamental master shared verbatim");
    expect(svg).toContain("Same four gilt ruby cardinal mounts");
    expect(svg).toContain(`for ${die}; no baked lettering`);
    expect(svg).toContain("<clipPath");
    expect(svg).toContain("url(#gold)");
    expect(svg).not.toMatch(/<image\b|<text\b|href=/);
    expect(classHitDieAsset(die)).toBe(`/card-art/class-dice/${die}-master-v28.svg`);
  });
  it("chooses only the verified record's actual die, regardless of class name",()=>{
    expect(CLASS_HIT_DICE).toEqual(["d4","d6","d8","d10","d12","d20"]);
    expect(normalizeClassHitDie("D 20")).toBe("d20");
    expect(classHitDieAsset("d100")).toBe("");
  });
  it("gives each die its own faceting while sharing the same ornamental frame",()=>{
    const svgByDie=CLASS_HIT_DICE.map(die=>readFileSync(masterPath(die),"utf8"));
    const ring=svgByDie.map(svg=>svg.match(/<circle cx="128" cy="128" r="109"[^>]+\/>/)?.[0]);
    expect(new Set(ring).size).toBe(1);
    expect(new Set(svgByDie).size).toBe(6);
  });
});
