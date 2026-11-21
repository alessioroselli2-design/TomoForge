// Guardrail: the feature renderer uses user-approved binary files.
// Never merge code that points to missing or wrong (non-transparent) assets.
import {readFileSync} from "fs";
import {resolve} from "path";

const loadPng=(asset)=>{
  const data=readFileSync(resolve(__dirname,"../../public",asset));
  expect(data.subarray(0,8)).toEqual(Buffer.from([137,80,78,71,13,10,26,10]));
  return {
    width:data.readUInt32BE(16),
    height:data.readUInt32BE(20),
    colorType:data[25],
  };
};
describe("feature master original files required for production",()=>{
  it("has the real user-approved class feature parchment master",()=>{
    const {width,height}=loadPng("card-art/master-privilegi-5x7.png");
    expect(width).toBe(1024);
    expect([1434,1536]).toContain(height);
  });
  it("has the high-resolution emblem with actual alpha transparency",()=>{
    const {width,height,colorType}=loadPng("emblemi/privilegi/simbolo-privilegi-alta-risoluzione.png");
    expect(width).toBeGreaterThanOrEqual(320);
    expect(height).toBeGreaterThanOrEqual(320);
    expect(colorType).toBe(6); // RGBA PNG
  });
});