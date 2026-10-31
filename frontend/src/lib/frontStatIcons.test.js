import { getFrontStatIcon } from "./frontStatIcons";
describe("approved stat medallions",()=>{
  test("CA and PF use isolated engraved SVG runes",()=>{
    expect(getFrontStatIcon("CA")).toBe("/card-art/stat-ca-clean-v24.svg");
    expect(getFrontStatIcon("PF")).toBe("/card-art/stat-pf-clean-v24.svg");
  });
  test("unrelated data fields keep their existing plain layout",()=>{
    expect(getFrontStatIcon("Vel.")).toBeNull();
    expect(getFrontStatIcon("Gittata")).toBeNull();
  });
});
