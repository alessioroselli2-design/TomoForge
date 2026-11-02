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
    expect(exporter).toContain('zoom:dragon?1.28:(data.type==="class"?1:1.2)');
    expect(base).toContain("font-size:clamp(14px,4.65cqw,16px)");
    // On the shared raster only the class icon shrinks, never the gold rim.
    expect(finalMaster).toContain('.tf-front-master-v17[data-front-category="class"] .tf-v3-medallion .tf-v3-sprite');
    expect(finalMaster).toContain('data-emblem-sprite="guerriero-crest"');
    expect(exporter).toContain('size:m.r*2*(s.sprite==="guerriero-crest"?1.08:');
    expect(component).toContain('data.type==="class"&&(!hasArtwork||artworkError)');
    expect(component).toContain('editorMode&&!hasArtwork');
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

describe("shared Monster master across every front",()=>{
 it("does not import or render another class master",()=>{
   expect(component).toContain('data-front-layout="unified-monster-master-v17"');
   expect(component).toContain('...frontBackground(data.type)');
   expect(component).not.toContain("class-master-v50");
   expect(component).not.toContain("tf-class-v40-master");
   expect(component).not.toContain('data-front-version="40"');
   expect(exporter).not.toContain("renderClassApprovedV40");
   expect(exporter).not.toContain("class-master-v50");
   expect(exporter).toContain("if(data.type===\"class\"){");
   expect(exporter).toContain("ctx.drawImage(jewel,240,335,72,75)");
 });
 it("keeps the Monster's approved raster as the sole active front art master",()=>{
   const root=resolve(__dirname,"../../public/card-art/");
   const monster=readFileSync(resolve(root,"front-master-v17.webp"));
   expect(monster.subarray(0,4).toString()).toBe("RIFF");
   expect(monster.subarray(8,12).toString()).toBe("WEBP");
   expect(monster.length).toBeGreaterThan(100000);
   expect(finalMaster).not.toContain(".tf-v39-class");
   expect(finalMaster).not.toContain("class-master-v50");
   expect(finalMaster).not.toContain("class-master-clean-v38");
   expect(finalMaster).toContain('data-front-category="class"');
 });
});
