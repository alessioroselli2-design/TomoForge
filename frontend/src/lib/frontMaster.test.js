import { FRONT_MASTER_URL, FRONT_DETAIL_REPAIR_URL, MASTER_REGIONS } from "./frontMaster";
describe("reference master front",()=>{
 it("uses one exact artwork asset, with dedicated dynamic locations",()=>{
  expect(FRONT_MASTER_URL).toBe("/card-art/front-master-v17.webp");
  expect(FRONT_DETAIL_REPAIR_URL).toBe("/card-art/front-detail-repair-v8.webp");
  expect(MASTER_REGIONS.art.w).toBeGreaterThan(270);
  expect(MASTER_REGIONS.emblem).toEqual({x:54,y:40,r:28});
  expect(MASTER_REGIONS.badge).toEqual({x:286,y:40,r:28});
  expect(MASTER_REGIONS.description.y).toBeGreaterThan(MASTER_REGIONS.detail.y);
  expect(MASTER_REGIONS.description.y+MASTER_REGIONS.description.h).toBeLessThan(476);
 });
});
