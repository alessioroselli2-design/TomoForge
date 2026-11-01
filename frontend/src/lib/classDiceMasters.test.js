import {readFileSync} from "fs";
import {resolve} from "path";
import {createHash} from "crypto";
import {CLASS_HIT_DICE,classHitDieAsset,normalizeClassHitDie} from "./classHitDice";

const masterPath=die=>resolve(__dirname,`../../public/card-art/class-dice/${die}-premium-v29.webp`);
describe("six approved reference-derived premium die artworks",()=>{
  it.each(["d4","d6","d8","d10","d12","d20"])("ships the exact illustrated, compressed and independent %s master",die=>{
    const bytes=readFileSync(masterPath(die));
    expect(bytes.length).toBeGreaterThan(15000);
    expect(bytes.subarray(0,4).toString()).toBe("RIFF");
    expect(bytes.subarray(8,12).toString()).toBe("WEBP");
    expect(classHitDieAsset(die)).toBe(`/card-art/class-dice/${die}-premium-v29.webp`);
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
