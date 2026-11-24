import {getBackComposition,backTipStyles,frontOpticalShift,cardArtBounds} from "./cardPrintGeometry";
import {APPROVED_BACK_FILES} from "./cardBacks";
describe("optical print alignment",()=>{
 it.each(APPROVED_BACK_FILES)("contains every source face and its repaired cap: %s",file=>{
  const c=getBackComposition(file);
  expect(c.x).toBeGreaterThanOrEqual(-1e-8);
  expect(c.y).toBeGreaterThanOrEqual(0);
  expect(c.x+c.w).toBeLessThanOrEqual(750+1e-8);
  expect(c.y+c.h).toBeLessThanOrEqual(1050+1e-8);
  expect(c.w/c.h).toBeCloseTo(c.crop.w/c.crop.h);
  if(c.tip){
   expect(c.tip.y).toBeGreaterThanOrEqual(-1e-8);
   expect(c.tip.y+c.tip.h).toBeCloseTo(c.y);
   expect(backTipStyles(file)).not.toBeNull();
  }else expect(file).toBe("classe");
 });
 it("preserves the legacy QR and all four outer trim edges",()=>{
  const shift=frontOpticalShift("monster");
  expect(456/476+shift).toBeLessThan(1);
  const b=cardArtBounds(1020,1428);
  expect(b.x).toBeCloseTo(20.4);
  expect(b.y).toBeCloseTo(28.56);
 });
});
