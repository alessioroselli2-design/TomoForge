import { getFrontStatIcon } from "./frontStatIcons";
describe("approved stat medallions",()=>{
  test("CA and PF use their own cropped source images",()=>{
    expect(getFrontStatIcon("CA")).toBe("/card-art/stat-ca.webp");
    expect(getFrontStatIcon("PF")).toBe("/card-art/stat-pf.webp");
  });
  test("unrelated data fields keep their existing plain layout",()=>{
    expect(getFrontStatIcon("Vel.")).toBeNull();
    expect(getFrontStatIcon("Gittata")).toBeNull();
  });
});
