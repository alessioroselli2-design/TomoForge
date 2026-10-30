import { FRONT_MASTER_URL, MASTER_REGIONS } from "./frontMaster";
describe("reference master front",()=>{
 it("uses one exact artwork asset, with dedicated dynamic locations",()=>{
  expect(FRONT_MASTER_URL).toBe("/card-art/front-master-v7.webp");
  expect(MASTER_REGIONS.art.w).toBeGreaterThan(270);
  expect(MASTER_REGIONS.description.y).toBeGreaterThan(MASTER_REGIONS.detail.y);
  expect(MASTER_REGIONS.description.y+MASTER_REGIONS.description.h).toBeLessThan(476);
 });
});
