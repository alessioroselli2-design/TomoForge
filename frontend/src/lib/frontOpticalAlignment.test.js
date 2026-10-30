import { readFileSync } from "fs";
import { resolve } from "path";

describe("v13 optical alignment on the approved front", () => {
  const css=readFileSync(resolve(__dirname, "../index.css"), "utf8");
  it("gives the long name a larger heading without moving the engraved cartouche",()=>{
    expect(css).toContain("font-size:clamp(15px,5.15cqw,19px)");
    expect(css).toContain(".tf-v3-medallion[data-emblem-sprite=\"drago-hd\"]");
  });
  it("keeps the PF enlarged icon concentric with CA",()=>{
    expect(css).toContain("left:calc(50% - 20px)");
    expect(css).toContain("width:24px;height:24px;");
  });
});

describe("v14 safe inset of title in engraved cartouche",()=>{
  const css=readFileSync(resolve(__dirname,"../index.css"),"utf8");
  it("keeps title and subtitle in a 44%-width well with nonzero inset",()=>{
    expect(css).toContain("left:28%;width:44%");
    expect(css).toContain("padding-inline:6px");
    expect(css).toContain("font-size:clamp(14px,4.65cqw,16px)");
    expect(css).toContain("font-size:7.7px;line-height:1.06");
  });
  it("uses perceptible optical offsets rather than pasting additional art",()=>{
    expect(css).toContain("transform:translate(2px,-1px) scale(.91)");
    expect(css).toContain("left:calc(50% - 20px)");
  });
});
