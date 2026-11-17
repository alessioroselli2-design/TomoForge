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
    expect(exporter).toContain('zoom:dragon?1.28:1.2');
    expect(base).toContain("font-size:clamp(14px,4.65cqw,16px)");
    // On the shared raster class emblems scale independently, never the gold rim.
    expect(finalMaster).toContain('.tf-front-master-v17[data-front-category="class"] .tf-class-original-emblem');
    expect(component).toContain('data-emblem-sprite={symbol?.sprite||"none"}');
    expect(exporter).toContain("size:m.r*2},");
    expect(component).toContain('data.type==="class"&&(!hasArtwork||artworkError)');
    expect(component).toContain('editorMode&&data.type!=="class"&&!hasArtwork');
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

describe("Class v2: one static printable composition",()=>{
 it("stores a SINGLE full-size fixed raster with no class overlays",()=>{
   const root=resolve(__dirname,"../../public/card-art/");
   const master=readFileSync(resolve(root,"master-classe-5x7-finale.png"));
   expect(master.subarray(1,4).toString()).toBe("PNG");
   expect(master.length).toBeGreaterThan(100000);
   const layouts=readFileSync(resolve(__dirname,"./frontCategoryLayouts.js"),"utf8");
   expect(layouts).toContain('master:"/card-art/master-classe-5x7-finale.png"');
   const exporter=readFileSync(resolve(__dirname,"./cardExport.js"),"utf8");
   expect(exporter).toContain('data.type==="class"?{x:19,y:84,w:303,h:138}:MASTER_REGIONS.art');
   expect(layouts).not.toContain('class-interior-v17.webp');
 });

 it("has one authoritative Class CSS block, no obsolete height cap and no scrolling",()=>{
   expect(finalMaster).not.toContain("max-height:49%");
   expect(finalMaster).not.toContain("overflow-y:auto");
   expect(finalMaster).toContain('.tf-front-master-v17[data-front-category="class"] .tf-v3-parchment .tf-v3-desc');
   expect(finalMaster).toContain("width:62%!important;height:25.5%!important;");
   expect(finalMaster).toContain("overflow:visible!important;");
   expect(finalMaster).toContain('data-stat-label="Competenze"');
   expect(finalMaster).toContain('.tf-front-master-v17[data-front-category="class"] .tf-v3-badge,');
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
   expect(exporter).toContain("ctx.drawImage(jewel,width*.833-size/2,height*.762-size/2,size,size)");
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

describe("Class 5x7 regression: Guerriero and Mago layout",()=>{
 it("uses exactly one 21%-wide class emblem, unmasked, and one 24%-wide die",()=>{
   const medalRules=finalMaster.match(/\.tf-front-master-v17\[data-front-category="class"\] \.tf-v3-medallion\{/g)||[];
   expect(medalRules).toHaveLength(1);
   expect(finalMaster).toContain('left:5.3%!important;top:2.6%!important;width:21%!important;');
   expect(finalMaster).toContain('left:83.3%!important;top:76.2%!important;');
   expect(finalMaster).toContain('width:24%!important;height:auto!important;aspect-ratio:1;');
   expect(finalMaster).toContain('-webkit-mask:none!important;mask:none!important;filter:none!important;transform:none!important;');
   expect(exporter).toContain('const badgeSize=width*.21;');
   expect(exporter).toContain('const size=width*.24;');
   expect(exporter).toContain('width*.833-size/2,height*.762-size/2');
 });
 it("keeps Guerriero's two 15px icons in a separate column with 3px vertical gap",()=>{
   expect(finalMaster).toContain('width:15px!important;height:15px!important;');
   expect(finalMaster).toContain('height:33px!important;gap:3px!important;');
   expect(finalMaster).toContain('justify-content:flex-start!important;gap:6px!important;');
   expect(finalMaster).toContain('flex:0 0 auto!important;flex-direction:column!important;');
   expect(finalMaster).toContain('flex:1 1 0!important;min-width:0!important;');
   expect(exporter).toContain('const iconSize=primary.length>1?15:20;');
   expect(exporter).toContain('const y=primary.length>1?statY+27+j*18:statY+32;');
   expect(exporter).toContain('const gap=6;');
 });
 it("keeps Mago's single icon at 20px without a second icon or shield",()=>{
   expect(finalMaster).toContain('width:20px!important;height:20px!important;');
   expect(component).toContain('const statIcon = isClass ? null : getFrontStatIcon(item.label)');
   expect(exporter).toContain('const src=data.type==="class"?null:getFrontStatIcon(it.label)');
   expect(component).toContain('getClassPrimaryAbilityIcons(item.fullValue || item.value)');
 });
});
