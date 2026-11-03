import { getFrontStatIcon } from "./frontStatIcons";
describe("approved stat medallions",()=>{
  test("CA and PF use isolated engraved SVG runes",()=>{
    expect(getFrontStatIcon("CA")).toBe("/card-art/stat-ca-clean-v24.svg");
    expect(getFrontStatIcon("PF")).toBe("/card-art/stat-pf-clean-v24.svg");
  });
  test("Class labels have their own readable icons",()=>{
    expect(getFrontStatIcon("Abilità primaria")).toBe("/card-art/class-stats/primary-v33.svg");
    expect(getFrontStatIcon("Tiri salvezza")).toBe("/card-art/class-stats/saves-v33.svg");
    expect(getFrontStatIcon("Competenze")).toBe("/card-art/class-stats/proficiencies-v33.svg");
  });
  test("unrelated data fields keep their existing plain layout",()=>{
    expect(getFrontStatIcon("Vel.")).toBeNull();
    expect(getFrontStatIcon("Gittata")).toBeNull();
  });
});
