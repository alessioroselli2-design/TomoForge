import { getFrontStatIcon } from "./frontStatIcons";
describe("approved stat medallions",()=>{
  test("CA and PF use isolated engraved SVG runes",()=>{
    expect(getFrontStatIcon("CA")).toBe("/card-art/stat-ca-clean-v24.svg");
    expect(getFrontStatIcon("PF")).toBe("/card-art/stat-pf-clean-v24.svg");
  });
  test("Class labels do not create duplicate overlays",()=>{
    expect(getFrontStatIcon("Abilità primaria")).toBeNull();
    expect(getFrontStatIcon("Tiri salvezza")).toBeNull();
    expect(getFrontStatIcon("Competenze")).toBeNull();
  });
  test("unrelated data fields keep their existing plain layout",()=>{
    expect(getFrontStatIcon("Vel.")).toBeNull();
    expect(getFrontStatIcon("Gittata")).toBeNull();
  });
});
