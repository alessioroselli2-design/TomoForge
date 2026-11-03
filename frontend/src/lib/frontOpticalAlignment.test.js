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
    expect(exporter).toContain('zoom:(dragon||data.type==="class")?1.28:1.2');
    expect(base).toContain("font-size:clamp(14px,4.65cqw,16px)");
    // On the shared raster class emblems scale independently, never the gold rim.
    expect(finalMaster).toContain('.tf-front-master-v17[data-front-category="class"] .tf-v3-medallion .tf-v3-sprite');
    expect(component).toContain('data-emblem-sprite={symbol?.sprite||"none"}');
    expect(exporter).toContain("size:m.r*2},");
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

describe("Class v2: one static printable composition",()=>{
 it("stores a SINGLE full-size fixed raster with no class overlays",()=>{
   const root=resolve(__dirname,"../../public/card-art/");
   const master=readFileSync(resolve(root,"class-master-user-final-20261103.jpg"));
   expect(master.subarray(0,3).toString("hex")).toBe("ffd8ff");
   expect(master.subarray(6,10).toString()).toBe("JFIF");
   expect(master.length).toBeGreaterThan(100000);
   // Byte-for-byte fingerprint of the image supplied and approved by the user.
   expect(require("crypto").createHash("sha256").update(master).digest("hex")).toBe("e0077e11a65cb716b951e56cdec86e4948074e4a55b01ea9b34183f7916c8b8b");
   const layouts=readFileSync(resolve(__dirname,"./frontCategoryLayouts.js"),"utf8");
   expect(layouts).toContain('master:"/card-art/class-master-user-final-20261103.jpg"');
   const exporter=readFileSync(resolve(__dirname,"./cardExport.js"),"utf8");
   expect(exporter).toContain('data.type==="class"?{x:13,y:86,w:314,h:135}:MASTER_REGIONS.art');
   expect(layouts).not.toContain('class-interior-v17.webp');
 });

 it("has one authoritative Class CSS block, no obsolete height cap and no scrolling",()=>{
   expect(finalMaster).not.toContain("max-height:49%");
   expect(finalMaster).not.toContain("overflow-y:auto");
   expect(finalMaster).toContain('.tf-front-master-v17[data-front-category="class"] .tf-v3-parchment .tf-v3-desc');
   expect(finalMaster).toContain("height:80%!important;");
   expect(finalMaster).toContain("max-height:80%!important;");
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
   expect(exporter).toContain("ctx.drawImage(jewel,249,327,76,80)");
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

describe("Originale immutabile carte Classe — campi indipendenti",()=>{
 it("usa soltanto il JPEG approvato senza coprirlo con sfondi e nuove caselle",()=>{
   const layouts=readFileSync(resolve(__dirname,"./frontCategoryLayouts.js"),"utf8");
   expect(layouts).toContain("class-master-user-final-20261103.jpg");
   expect(finalMaster).toContain('data-front-category="class"] .tf-v3-stats');
   expect(finalMaster).toContain("grid-template-columns:34% 31% 35%");
   expect(finalMaster).toContain('data-front-category="class"] .tf-v3-picture::after{display:none!important}');
   expect(component).toContain('data.type!=="class"');
 });
});
describe("Classe: medaglione ottico al livello del Drago Rosso",()=>{
 it("uses the signed-off 168px Warrior shield instead of the rejected SVG",()=>{
   const mapping=readFileSync(resolve(__dirname,"./frontEmblems.js"),"utf8");
   expect(mapping).toContain('/card-art/guerriero-reference-original-v36.webp');
   expect(mapping).not.toContain('guerriero-crest-optical-v2.svg');
 });
 it("gives class icons the same 1.28 enlargement as Dragon without scaling the outer ring",()=>{
   const classBlock=finalMaster.slice(finalMaster.lastIndexOf('Master Classe firmato 03/11/2026'));
   expect(classBlock).toContain('width:16.47059%!important');
   expect(classBlock).toContain('transform:scale(1.28)!important');
   expect(classBlock).toContain('background:transparent!important;border:0!important;box-shadow:none!important');
   expect(exporter).toContain('zoom:(dragon||data.type==="class")?1.28:1.2');
   expect(exporter).toContain('x:data.type==="class"?52:m.x,y:data.type==="class"?47:m.y');
 });
});
