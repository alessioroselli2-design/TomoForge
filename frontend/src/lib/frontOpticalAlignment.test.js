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

describe("dedicated class front only",()=>{
 it("uses a single long parchment and d10 gem without modifying monster master",()=>{
   expect(finalMaster).toContain('[data-front-category="class"] .tf-v3-parchment');
   expect(component).toContain("data.classDieAsset?");
   expect(component).toContain("data.showDescriptionLabel&&");
   expect(exporter).toContain('if(data.type==="class"){');
   expect(exporter).toContain("src:data.classDieAsset");
 });
});

describe("v33 class frame optical safety",()=>{
 it("does not extend the class parchment over the lower carved frame",()=>{
   expect(finalMaster).toContain('top:59.24370%!important;height:34.45378%!important');
   expect(finalMaster).toContain('inset:3.5% 3.2% 6.5% 3.2%!important');
   expect(finalMaster).toContain('height:17.45%!important');
   expect(finalMaster).toContain('top:29%!important;right:3.4%!important');
 });
});

describe("v36 Class frame uses actual approved engraved plate",()=>{
  it("renders a dedicated reference-backed image beneath real data",()=>{
    expect(component).toContain('className="tf-v39-class-master"');
    expect(component).toContain('class-master-reference-v39.webp');
    expect(finalMaster).toContain('content:none!important;display:none!important');
    expect(exporter).toContain('ctx.drawImage(master,0,0,width,height)');
  });
  it("avoids drawing solid rectangles that cover carved parchment and bottom rail",()=>{
    expect(exporter).not.toContain('ctx.fillRect(23,199,294,75)');
    expect(exporter).not.toContain('ctx.fillRect(30,290,280,135)');
  });
});


describe("Class v38 anti-overlap contract",()=>{
  it("uses a full-canvas lower master and leaves no obsolete v36 image node",()=>{
    const plate=readFileSync(resolve(__dirname,"../../public/card-art/class-master-reference-v39.webp"));
    expect(plate.subarray(0,4).toString()).toBe("RIFF");
    expect(plate.subarray(8,12).toString()).toBe("WEBP");
    expect(plate.length).toBeGreaterThan(50000);
    expect(component).toContain('className="tf-v39-class-master"');
    expect(component).not.toContain('className="tf-v36-class-master"');
    expect(exporter).toContain('ctx.drawImage(master,0,0,width,height)');
    expect(finalMaster).toContain('top:53.4%!important;left:5.4%!important');
    expect(finalMaster).toContain('left:5.5%!important;top:69.2%!important');
    expect(finalMaster).toContain('content:none!important;display:none!important');
  });
});

describe("v39 user-approved Class card, without the circled lower footer",()=>{
 it("loads exactly one reference-derived master and preserves an independent artwork well",()=>{
   const asset=readFileSync(resolve(__dirname,"../../public/card-art/class-master-reference-v39.webp"));
   expect(asset.subarray(0,4).toString()).toBe("RIFF");
   expect(asset.length).toBeGreaterThan(50000);
   expect(component).toContain('className="tf-v39-class-master"');
   expect(component).not.toContain('className="tf-v38-class-master"');
   expect(component).toContain('previewApprovedArtwork');
   expect(exporter).toContain('if(data.type==="class")return renderClassReferenceV39(element,card,data)');
   expect(exporter).toContain('/card-art/class-master-reference-v39.webp');
   expect(finalMaster).toContain('top:53.4%!important;left:5.4%!important');
   expect(finalMaster).toContain('left:5.5%!important;top:69.2%!important');
 });
});
