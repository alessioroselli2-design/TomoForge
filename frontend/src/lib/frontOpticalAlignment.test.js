import { readFileSync } from "fs";
import { resolve } from "path";

const base=readFileSync(resolve(__dirname,"../index.css"),"utf8");
const finalMaster=readFileSync(resolve(__dirname,"../frontMasterV17.css"),"utf8");
const exporter=readFileSync(resolve(__dirname,"./cardExport.js"),"utf8");
const component=readFileSync(resolve(__dirname,"../components/TradingCard.jsx"),"utf8");

describe("TomoForge approved ornate master",()=>{
  it("preserves the signed-off dragon medallion and title parchment",()=>{
    expect(finalMaster).toContain('data-emblem-sprite="drago-hd"');
    expect(finalMaster).toContain("transform:scale(1.28)!important");
    expect(finalMaster).toContain("circle closest-side at center");
    expect(exporter).toContain('zoom:dragon?1.28:(s.sprite==="guerriero-hd"?1.0:1.2)');
    expect(base).toContain("font-size:clamp(14px,4.65cqw,16px)");
  });
  it("preserves the existing three parchment columns",()=>{
    expect(finalMaster).toContain("grid-template-columns:32% 35% 33%");
    expect(finalMaster).toContain("height:8.82353%");
  });
});

describe("v24 clean stat symbols within the existing parchment",()=>{
  it("places each icon and number in one centered flex value row",()=>{
    expect(component).toContain('className="tf-v6-stat-value-row"');
    expect(component).toContain("getFrontStatIcon(item.label)");
    expect(finalMaster).toContain("display:inline-flex!important");
    expect(finalMaster).toContain("gap:5px!important");
    expect(finalMaster).toContain("width:17px!important");
    expect(finalMaster).toContain("position:static!important");
    expect(finalMaster).toContain("clip-path:none!important");
    expect(finalMaster).toContain("mask-image:none!important");
  });
  it("prints exactly the same aligned rune-plus-value group",()=>{
    expect(exporter).toContain("const groupWidth=runeSize+gap+renderedTextWidth");
    expect(exporter).toContain("ctx.drawImage(icon,runeLeft,statY+19,runeSize,runeSize)");
    expect(exporter).toContain("drawFittedText(ctx,it.value,valueCenter,statY+32,valueMaxWidth,icon?14:13");
  });
});

describe("v25 small subtitle raise — no ornament overlap",()=>{
  it("raises only the subtitle by three logical pixels without moving the title or approved frame",()=>{
    expect(finalMaster).toContain('.tf-front-master-v17 .tf-v3-titles p{font-size:7.8px;line-height:1.1;color:#422b1d;position:relative;top:-3px}');
    expect(finalMaster).toContain('.tf-front-master-v17 .tf-v3-titles{left:28%!important;top:3.6%!important;width:44%!important;height:9.15%!important;transform:none!important;gap:2px}');
  });
  it("matches the same 3px lift when exported in PNG and PDF",()=>{
    expect(exporter).toContain('drawFittedText(ctx,data.subtitle,MASTER_REGIONS.subtitle.x,MASTER_REGIONS.subtitle.y-4,');
    expect(exporter).toContain('drawFittedText(ctx,data.name,MASTER_REGIONS.title.x,MASTER_REGIONS.title.y+5,');
  });
});

describe("Class v50: SAME Monster artwork-window geometry across categories",()=>{
 const css=readFileSync(resolve(__dirname,"../classApprovedV40.css"),"utf8");
 const frameScope=exporter.slice(exporter.indexOf("async function renderClassApprovedV40"),exporter.indexOf("async function renderApprovedMaster"));
 it("reuses the approved Monster picture's gold edges, without changing Class-only wells",()=>{
   expect(component).toContain('data-front-layout="single-approved-master-v40"');
   expect(component).toContain('className="tf-class-v40-master"');
   expect(component).toContain('"/card-art/class-master-v50-approved-empty.webp"');
   expect(component).toContain('"/card-art/class-master-v50-approved-window.webp"');
   expect(component).not.toContain('className="tf-v39-class-master"');
   expect(css).toContain("top:56.0%;width:89.5%;height:6.6%");
   expect(css).toContain(".tf-class-v40-description");
   expect(css).toContain("-webkit-line-clamp:3");
   expect(exporter).toContain("wrapTextLines(ctx,value,maxWidth[i]).slice(0,3)");
 });
 it("stores two valid interchangeable rasters, with a REAL transparent artwork aperture",()=>{
   const empty=readFileSync(resolve(__dirname,"../../public/card-art/class-master-v50-approved-empty.webp"));
   const alpha=readFileSync(resolve(__dirname,"../../public/card-art/class-master-v50-approved-window.webp"));
   for(const bytes of [empty,alpha]){
     expect(bytes.subarray(0,4).toString()).toBe("RIFF");
     expect(bytes.subarray(8,12).toString()).toBe("WEBP");
     expect(bytes.length).toBeGreaterThan(100000);
   }
   expect(alpha.toString("ascii",12,16)).toBe("VP8X");
   expect(alpha[20]&0x10).toBe(0x10);
   expect(Buffer.compare(empty,alpha)).not.toBe(0);
 });
 it("never adds a second border, approximation, or legacy Class image mask",()=>{
   expect(css).toContain("z-index:1;left:4.75%;top:17.0%");
   expect(css).toContain("width:90.5%;height:28.5%");
   expect(css).toContain(".tf-class-v40-master");
   expect(css).not.toContain("class-art-window-mask-v46.png");
   expect(css).not.toContain("border-radius:4.45% / 9.6%");
   expect(frameScope).not.toContain("windowMask");
   expect(frameScope).not.toContain('globalCompositeOperation="destination-in"');
   expect(frameScope).not.toContain("ctx.quadraticCurveTo");
   expect(frameScope.indexOf("ctx.drawImage(art,")).toBeLessThan(frameScope.indexOf("ctx.drawImage(master,0,0,width,height)"));
   expect(frameScope).toContain("/card-art/class-master-v50-approved-empty.webp");
   expect(frameScope).toContain("/card-art/class-master-v50-approved-window.webp");
   expect(frameScope).toContain("const x=width*.0475,y=height*.17,w=width*.905,h=height*.285;");
   expect(css).toContain("top:64.4%");
   expect(frameScope).toContain("height*.666");
 });
});
