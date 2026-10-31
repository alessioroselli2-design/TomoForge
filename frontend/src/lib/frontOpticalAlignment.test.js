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
    expect(css).toContain("transform:scale(1.23)");
    expect(css).toContain("left:calc(50% - 23px)");
  });
});

describe("v15 centered medallions and clean stat discs",()=>{
  const css=readFileSync(resolve(__dirname,"../index.css"),"utf8");
  const print=readFileSync(resolve(__dirname,"./cardExport.js"),"utf8");
  it("fills the approved dragon circle without removing the GS badge",()=>{
    expect(css).toContain("transform:scale(1.23)");
    expect(print).toContain("dragon?.26:.275");
    expect(print).toContain("if(data.badge)");
  });
  it("centers CA/PF equally and crops the peripheral tile fringe in preview and print",()=>{
    expect(css).toContain('[data-stat-label="CA"] .tf-v6-stat-icon,');
    expect(css).toContain('[data-stat-label="PF"] .tf-v6-stat-icon');
    expect(css).toContain("left:calc(50% - 11px);top:50%");
    expect(css).toContain("clip-path:circle(34% at 50% 50%)");
    expect(css).toContain("filter:none!important");
    expect(css).toContain("width:44px;height:44px");
    expect(css).toContain("transform:translate(-50%,-50%)");
    expect(print).toContain("iconX=cx-25,iconY=statY+MASTER_REGIONS.stats.h/2");
    expect(print).toContain("{x:iconX,y:iconY,size:30},.23,.38");
  });
});

describe("v22: integrated symbols on the ornate hi-res master",()=>{
 const css=readFileSync(resolve(__dirname,"../index.css"),"utf8");
 const exportSource=readFileSync(resolve(__dirname,"./cardExport.js"),"utf8");
 it("blends the dragon into the crimson recess instead of adding a second ring",()=>{
  expect(css).toContain('.tf-front-master-v17 .tf-v3-medallion[data-emblem-sprite="drago-hd"] .tf-v3-sprite');
  expect(css).toContain('transform:none!important');
  expect(css).toContain('transparent 80%');
  expect(exportSource).toContain('layer.globalCompositeOperation="destination-in"');
  expect(exportSource).toContain('drawIntegratedMedallion(ctx,icon,');
 });
 it("keeps small CA/PF runes aligned to the printable statistics",()=>{
  expect(css).toContain('width:30px!important;height:30px!important');
  expect(css).toContain('left:calc(50% - 25px)!important;top:50%!important');
  expect(css).toContain('flex:0 0 32%!important');
  expect(css).toContain('flex:0 0 35%!important');
  expect(exportSource).toContain('{x:iconX,y:iconY,size:30},.23,.38');
 });
});
