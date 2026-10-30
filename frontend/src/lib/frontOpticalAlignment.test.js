import { readFileSync } from "fs";
import { resolve } from "path";

describe("v13 optical alignment on the approved front", () => {
  const css=readFileSync(resolve(__dirname, "../index.css"), "utf8");
  it("gives the long name a larger heading without moving the engraved cartouche",()=>{
    expect(css).toContain("font-size:clamp(15px,5.15cqw,19px)");
    expect(css).toContain(".tf-v3-medallion[data-emblem-sprite=\"drago-hd\"]");
  });
  it("keeps the PF enlarged icon concentric with CA",()=>{
    expect(css).toContain("left:calc(50% - 23px)");
    expect(css).toContain("width:24px;height:24px;");
  });
});

describe("v14 safe inset of title in engraved cartouche",()=>{
  const css=readFileSync(resolve(__dirname,"../index.css"),"utf8");
  it("keeps title and subtitle in a 44%-width well with nonzero inset",()=>{
    expect(css).toContain("left:28%;width:44%;top:4%");
    expect(css).toContain("padding-inline:6px");
    expect(css).toContain("font-size:clamp(14px,4.65cqw,16px)");
    expect(css).toContain("font-size:7.7px;line-height:1.06");
  });
  it("uses perceptible optical offsets rather than pasting additional art",()=>{
    expect(css).toContain("transform:scale(1.06)");
    expect(css).toContain("left:calc(50% - 23px)");
  });
});

describe("v15 centered medallions and clean stat discs",()=>{
  const css=readFileSync(resolve(__dirname,"../index.css"),"utf8");
  const print=readFileSync(resolve(__dirname,"./cardExport.js"),"utf8");
  it("fills the approved dragon circle without removing the GS badge",()=>{
    expect(css).toContain("transform:scale(1.06)");
    expect(print).toContain("dragon?1.06:1");
    expect(print).toContain("if(data.badge)");
  });
  it("centers CA/PF equally and crops the peripheral tile fringe in preview and print",()=>{
    expect(css).toContain('[data-stat-label="CA"] .tf-v6-stat-icon,');
    expect(css).toContain('[data-stat-label="PF"] .tf-v6-stat-icon');
    expect(css).toContain("left:calc(50% - 26px);top:50%");
    expect(css).toContain("clip-path:circle(44% at 50% 50%)");
    expect(css).toContain("filter:none");
    expect(print).toContain("iconX=cx-11,iconY=statY+MASTER_REGIONS.stats.h/2");
    expect(print).toContain("ctx.arc(iconX,iconY,diameter*.44");
  });
});
