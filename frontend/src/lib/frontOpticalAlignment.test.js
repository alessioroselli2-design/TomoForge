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
