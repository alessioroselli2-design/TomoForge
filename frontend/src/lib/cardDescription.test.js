import { publicDescriptionUrl } from "./cardDescription";
describe("public printed QR destinations",()=>{
  it("requires a saved card",()=>{
    expect(publicDescriptionUrl({type:"monster"})).toBe("");
    expect(publicDescriptionUrl({id:""})).toBe("");
  });
  it("uses the stable public description page, never the editor or private library",()=>{
    expect(publicDescriptionUrl({id:"84a1-20",reference_ids:["private"]}))
      .toBe("https://tomo-forge.vercel.app/d/84a1-20");
  });
});
