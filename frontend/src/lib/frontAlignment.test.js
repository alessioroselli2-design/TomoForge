import { MASTER_REGIONS } from "./frontMaster";
describe("approved card alignment", () => {
  test("both top medallions use identical radius and symmetric centres", () => {
    expect(MASTER_REGIONS.emblem.r).toBe(MASTER_REGIONS.badge.r);
    expect(MASTER_REGIONS.emblem.x+MASTER_REGIONS.badge.x).toBe(340);
    expect(MASTER_REGIONS.emblem.y).toBe(MASTER_REGIONS.badge.y);
  });
  test("icon wells retain the same 3-column stat partition", () => {
    expect(MASTER_REGIONS.stats.w).toBe(304);
    expect(MASTER_REGIONS.stats.x).toBe(18);
  });
});
