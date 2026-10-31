import { getFrontStatIcon } from "./frontStatIcons";
describe("approved stat medallions",()=>{
  test("CA and PF use isolated engraved SVG runes",()=>{
    expect(getFrontStatIcon("CA")).toBe("/card-art/stat-ca-rune-v23.svg");
    expect(getFrontStatIcon("PF")).toBe("/card-art/stat-pf-rune-v23.svg");
  });
  test("unrelated data fields keep their existing plain layout",()=>{
    expect(getFrontStatIcon("Vel.")).toBeNull();
    expect(getFrontStatIcon("Gittata")).toBeNull();
  });
});
