// Regression tests for v9 polish: no new asset, duplicate footer or CSS sticker.
import { readFileSync } from "fs";
import { resolve } from "path";

const css=readFileSync(resolve(__dirname,"../index.css"),"utf8");
describe("approved master front final polish",()=>{
  it("keeps the approved master and the repaired parchment without adding a replacement box",()=>{
    expect(css).toContain("v9 final front polish");
    expect(css).toContain(".tf-front-master-v7 .tf-v5-detail-cell span");
    expect(css).toContain(".tf-front-master-v7 .tf-v3-stat[data-stat-label=\"Vel.\"] strong");
    expect(css).not.toContain(".tf-front-master-v9 .tf-v5-bottom-rail");
  });
});