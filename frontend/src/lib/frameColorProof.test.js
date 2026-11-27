import fs from "fs";
import path from "path";
import {ARMOR_METAL_LAYER, bronzeTrimColor} from "./frameColorProof";
import palette from "./armorProofPalette.json";

test("armour colour separation is a native-size lossless layer with alpha",()=>{
 const bytes=fs.readFileSync(path.resolve(process.cwd(),"public"+ARMOR_METAL_LAYER));
 expect(bytes.toString("ascii",8,16)).toBe("WEBPVP8L");
 const packed=bytes.readUInt32LE(21);
 expect([(packed&16383)+1,((packed>>>14)&16383)+1]).toEqual([2040,2856]);
 expect((packed>>>28)&1).toBe(1);
});

test("the exterior trim uses the same shadow, midtone and highlight samples as the engraving",()=>{
 palette.knots.forEach((value,i)=>{
  expect(bronzeTrimColor(value,value,value)).toEqual(palette.colors[i]);
 });
});

import {METAL_PROOF_TYPES,metalProofUrl} from "./frameColorProof";
test("every supported category has a native-sized lossless metal layer; nine unique masters",()=>{
 const urls=new Set(METAL_PROOF_TYPES.map(metalProofUrl));
 expect(urls.size).toBe(9);
 for(const url of urls){
  const bytes=fs.readFileSync(path.resolve(process.cwd(),"public"+url));
  expect(bytes.toString("ascii",8,16)).toBe("WEBPVP8L");
  const packed=bytes.readUInt32LE(21);
  expect([(packed&16383)+1,((packed>>>14)&16383)+1]).toEqual([2040,2856]);
  expect((packed>>>28)&1).toBe(1);
 }
 expect(metalProofUrl("subclass")).toBe(metalProofUrl("class"));
 expect(metalProofUrl("character")).toBe(metalProofUrl("monster"));
});
