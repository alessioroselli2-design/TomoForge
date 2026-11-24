import jsPDF from "jspdf";
import { CARD_ART_SCALE } from "./cardPrintGeometry";
import { PRESS_SPEC, getPressLayout, setPressPageBoxes } from "./pressGeometry";

describe("professional PDF geometry",()=>{
  it("keeps the original artwork undistorted and at least 3 mm inside trim",()=>{
    const p=PRESS_SPEC, r=getPressLayout();
    expect(p.pageWidth).toBe(p.trimWidth+2*p.bleed);
    expect(p.pageHeight).toBeCloseTo(p.trimHeight+2*p.bleed);
    expect(r.w/r.h).toBeCloseTo(5/7);
    expect(r.x+r.w/2).toBeCloseTo(p.pageWidth/2);
    expect(r.y+r.h/2).toBeCloseTo(p.pageHeight/2);
    expect(r.x+(1-CARD_ART_SCALE)*r.w/2-p.bleed).toBeGreaterThanOrEqual(p.safe-1e-9);
    expect(r.y+(1-CARD_ART_SCALE)*r.h/2-p.bleed).toBeGreaterThanOrEqual(p.safe-1e-9);
  });
  it("writes real TrimBox and BleedBox metadata on every PDF page",()=>{
    const p=PRESS_SPEC, pdf=new jsPDF({unit:"mm",format:[p.pageWidth,p.pageHeight]});
    for(let i=0;i<4;i++){
      if(i)pdf.addPage([p.pageWidth,p.pageHeight],"portrait");
      setPressPageBoxes(pdf);
    }
    const raw=pdf.output();
    expect(raw.match(/\/TrimBox \[/g)).toHaveLength(4);
    expect(raw.match(/\/BleedBox \[/g)).toHaveLength(4);
    const trim=raw.match(/\/TrimBox \[([^\]]+)\]/)[1].trim().split(/\s+/).map(Number);
    expect((trim[2]-trim[0])*25.4/72).toBeCloseTo(p.trimWidth);
    expect((trim[3]-trim[1])*25.4/72).toBeCloseTo(p.trimHeight);
  });
});
