import {getBackCrop,frontMasterSlices,getCutGuideLines} from "./cardPrintGeometry";
import {APPROVED_BACK_FILES} from "./cardBacks";
describe("full trim geometry",()=>{
 it.each(APPROVED_BACK_FILES)("retains the same 5:7 source crop: %s",file=>{
  const r=getBackCrop(file);
  expect(r.x).toBeGreaterThanOrEqual(0);expect(r.y).toBeGreaterThanOrEqual(0);
  expect(r.x+r.w).toBeLessThanOrEqual(750);expect(r.y+r.h).toBeLessThanOrEqual(1050);
  expect(r.w/r.h).toBeCloseTo(5/7);
 });
 it.each(["monster","character","class","custom"])("moves only the lower master strip to trim: %s",type=>{
  const [a,b]=frontMasterSlices(type);
  expect(a.y+a.h).toBeCloseTo(b.y);
  expect(b.y+b.h).toBeCloseTo(1);
  expect(b.h).toBeCloseTo(b.sourceH);
 });
 it("puts eight short guides strictly outside the card, aligned to its edges",()=>{
  const b={x:12,y:18,w:63.5,h:88.9};
  const lines=getCutGuideLines(b);
  expect(lines).toHaveLength(8);
  lines.forEach(([x1,y1,x2,y2])=>{
   expect(Math.hypot(x2-x1,y2-y1)).toBeCloseTo(1.05);
   expect(x1===x2?(y1<b.y&&y2<b.y||y1>b.y+b.h&&y2>b.y+b.h):(x1<b.x&&x2<b.x||x1>b.x+b.w&&x2>b.x+b.w)).toBe(true);
  });
 });
});
