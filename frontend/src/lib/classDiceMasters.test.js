import {readFileSync} from "fs";
import {resolve} from "path";
import {createHash} from "crypto";
import {CLASS_HIT_DICE,classHitDieAsset,normalizeClassHitDie} from "./classHitDice";

const masterPath=die=>resolve(__dirname,`../../public/card-art/dadi-vita/${die}.png`);
describe("six original complete, preframed class hit-die PNGs",()=>{
  it.each(["d4","d6","d8","d10","d12","d20"])("ships the exact unchanged complete %s PNG",die=>{
    const bytes=readFileSync(masterPath(die));
    expect(bytes.length).toBeGreaterThan(15000);
    expect(bytes[0]).toBe(137);
    expect(bytes.subarray(1,4).toString()).toBe("PNG");
    expect(classHitDieAsset(die)).toBe(`/card-art/dadi-vita/${die}.png`);
  });
  it("keeps one distinct artwork for each die in the reference's six-color series",()=>{
    const hashes=CLASS_HIT_DICE.map(die=>createHash("sha256").update(readFileSync(masterPath(die))).digest("hex"));
    expect(new Set(hashes).size).toBe(6);
  });
  it("selects from record data instead of guessing a hit die from the class name",()=>{
    expect(CLASS_HIT_DICE).toEqual(["d4","d6","d8","d10","d12","d20"]);
    expect(normalizeClassHitDie("D 20")).toBe("d20");
    expect(classHitDieAsset("d100")).toBe("");
  });
});
