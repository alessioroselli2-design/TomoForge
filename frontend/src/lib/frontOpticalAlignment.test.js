import { readFileSync } from "fs";
import { createHash } from "crypto";
import { resolve } from "path";

const base=readFileSync(resolve(__dirname,"../index.css"),"utf8");
const finalMaster=readFileSync(resolve(__dirname,"../frontMasterV17.css"),"utf8");
const exporter=readFileSync(resolve(__dirname,"./cardExport.js"),"utf8");
const component=readFileSync(resolve(__dirname,"../components/TradingCard.jsx"),"utf8");

describe("TomoForge approved ornate master",()=>{
  it("preserves the title parchment and the original class emblem",()=>{
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
   const master=readFileSync(resolve(root,"master-classe-5x7-senza-muscolo-e-anello-20261118.jpg"));
   expect(master.subarray(0,3).toString("hex")).toBe("ffd8ff");
   // Byte-for-byte original supplied on 18 Nov: no baked-in muscle or die ring.
   expect(createHash("sha256").update(master).digest("hex"))
     .toBe("3c09a20c755529c8b8a4344b80f49ddf0b1a94d2efc7dadb8ac6c8c7479827ab");
   expect(master.length).toBeGreaterThan(100000);
   const layouts=readFileSync(resolve(__dirname,"./frontCategoryLayouts.js"),"utf8");
   expect(layouts).toContain('master:"/card-art/master-classe-5x7-senza-muscolo-e-anello-20261118.jpg"');
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
   expect(exporter).toContain("ctx.drawImage(jewel,x-diameter/2,y-diameter/2,diameter,diameter);");
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

describe("Class 5x7 regression: Guerriero, Mago, Paladino and Ranger",()=>{
 it("centers the 26% HD class emblem above the master ring",()=>{
   const medalRules=finalMaster.split('.tf-front-master-v17[data-front-category="class"] .tf-v3-medallion{');
   expect(medalRules).toHaveLength(2);
   expect(finalMaster).toContain('left:2.8%!important;top:0.814286%!important;width:26%!important;');
   expect(finalMaster).toContain('height:auto!important;aspect-ratio:1!important;z-index:14!important;');
   expect(finalMaster).toContain('overflow:visible!important;border-radius:0!important;');
   expect(finalMaster).toContain('mask:none!important;-webkit-mask:none!important;clip-path:none!important;');
   expect(finalMaster).toContain('left:83.3%!important;top:76.2%!important;');
   expect(finalMaster).toContain('width:28.3%!important;height:auto!important;aspect-ratio:1;');
   expect(finalMaster).toContain('overflow:visible!important;clip-path:none!important;');
   expect(finalMaster).toContain('mask:none!important;-webkit-mask:none!important;filter:none!important;');
   expect(finalMaster).toContain('-webkit-mask:none!important;mask:none!important;filter:none!important;transform:none!important;');
   expect(exporter).toContain('const badgeSize = width * (data.type === "spell" ? 0.255 : 0.26);');
   expect(exporter).toContain('const diameter=width*.283,x=width*.833,y=height*.762;');
   expect(exporter).toContain('ctx.drawImage(jewel,x-diameter/2,y-diameter/2,diameter,diameter);');
   expect(exporter).not.toContain('sourceSide=Math.min(jewel.naturalWidth,jewel.naturalHeight)*.65;');
 });
 it("places two original 22px PNGs side by side, with 6px between them and one line of text",()=>{
   expect(finalMaster).toContain('width:22px!important;height:22px!important;');
   expect(finalMaster).toContain('flex-direction:row!important;gap:6px!important;height:22px!important;');
   expect(finalMaster).toContain('top:22%!important;min-height:49px!important;height:49px!important;');
   expect(finalMaster).toContain('white-space:nowrap!important;overflow-wrap:normal!important;');
   expect(exporter).toContain('const size=22,gap=6,items=primary.slice(0,2);');
   expect(exporter).toContain('ctx.drawImage(asset,iconStart+j*(size+gap),statY+16,size,size)');
 });
 it("uses Mago's original 26px PNG to the left of the ability text, without extra shield",()=>{
   expect(finalMaster).toContain('width:26px!important;height:26px!important;');
   expect(finalMaster).toContain('object-fit:contain!important;object-position:center!important;');
   expect(finalMaster).toContain('mask:none!important;-webkit-mask:none!important;clip-path:none!important;');
   expect(component).toContain('const statIcon = isClass ? null : getFrontStatIcon(item.label)');
   expect(exporter).toContain('const src=data.type==="class"?null:getFrontStatIcon(it.label)');
   expect(exporter).toContain('const size=26,gap=6,text=String(it.value||"");');
   expect(component).toContain('getClassPrimaryAbilityIcons(item.fullValue || item.value)');
 });
});
