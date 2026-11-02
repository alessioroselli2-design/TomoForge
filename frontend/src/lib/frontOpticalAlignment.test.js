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

describe("v40 Class has ONE authoritatively approved master",()=>{
 it("uses independent layout that cannot inherit any v17/33/36/38/39 frame",()=>{
   expect(component).toContain('data-front-layout="single-approved-master-v40"');
   expect(component).toContain('className="tf-class-v40-master"');
   expect(component).toContain('class-approved-single-master-v40.webp');
   expect(component).toContain('if(data.type==="class")');
   expect(component).not.toContain('className="tf-v39-class-master"');
   expect(component).not.toContain('className="tf-v38-class-master"');
   expect(component).not.toContain('className="tf-v36-class-master"');
 });
 it("uses one exact ornamental image without the circled lower extension",()=>{
   const asset=readFileSync(resolve(__dirname,"../../public/card-art/class-approved-single-master-v40.webp"));
   expect(asset.subarray(0,4).toString()).toBe("RIFF");
   expect(asset.subarray(8,12).toString()).toBe("WEBP");
   expect(asset.length).toBeGreaterThan(50000);
   expect(exporter).toContain('renderClassApprovedV40(element,card)');
   expect(exporter).toContain('/card-art/class-approved-single-master-v40.webp');
   expect(exporter).not.toContain('renderClassReferenceV39');
 });
});

describe("Class v40 dynamic content stays INSIDE approved master",()=>{
 const css=readFileSync(resolve(__dirname,"../classApprovedV40.css"),"utf8");
 it("keeps the original one-piece artwork and hides its baked sample until selected",()=>{
   expect(component).toContain('data-testid="front-artwork-empty"');
   expect(component).not.toContain("previewApprovedArtwork");
   expect(css).toContain(".tf-class-v40-art-empty{position:absolute;inset:0;background:");
   expect(exporter).toContain("The master contains a baked sample Warrior illustration.");
 });
 it("aligns all 3 inset values and bounds them to their ORIGINAL gold wells",()=>{
   expect(css).toContain("top:56.0%;width:89.5%;height:6.6%");
   expect(css).toContain("pointer-events:none;overflow:hidden");
   expect(css).toContain("-webkit-line-clamp:3");
   expect(exporter).toContain("wrapTextLines(ctx,value,maxWidth[i]).slice(0,3)");
   expect(exporter).toContain("const first=height*.587");
 });
});
