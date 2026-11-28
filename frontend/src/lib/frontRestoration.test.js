import fs from "fs";
import path from "path";
import {frontBackground,restoredFrontMaster} from "./frontCategoryLayouts";
import {frontMaskSource,paintNativeFrontBackground} from "./frontExterior";

const types=["monster","class","subclass","character","spell","feature","race","feat","item","weapon","armor"];
const files=new Set(types.map(t=>restoredFrontMaster(frontMaskSource(t).src)));
test("all eleven categories share exactly nine restored masters and retain their originals",()=>{
 expect(files.size).toBe(9);
 for(const type of types){
  const original=frontMaskSource(type).src;
  expect(fs.existsSync(path.resolve(process.cwd(),"public"+original))).toBe(true);
  const bytes=fs.readFileSync(path.resolve(process.cwd(),"public"+restoredFrontMaster(original)));
  expect(bytes.toString("ascii",0,4)).toBe("RIFF");
  expect(bytes.toString("ascii",8,12)).toBe("WEBP");
  const kind=bytes.toString("ascii",12,16);
  const dims=kind==="VP8X"?[1+bytes.readUIntLE(24,3),1+bytes.readUIntLE(27,3)]:[bytes.readUInt16LE(26)&16383,bytes.readUInt16LE(28)&16383];
  expect(dims).toEqual([2040,2856]);
 }
 expect(frontBackground("class").backgroundImage).toContain(restoredFrontMaster(frontMaskSource("class").src));
});
test("native master is painted underneath the foreground at final PNG resolution",()=>{
 const ctx={save:jest.fn(),restore:jest.fn(),setTransform:jest.fn(),drawImage:jest.fn()};
 const canvas={width:1020,height:1428,getContext:()=>ctx};
 const image={naturalWidth:2040,naturalHeight:2856};
 paintNativeFrontBackground(canvas,image);
 expect(ctx.globalCompositeOperation).toBe("destination-over");
 expect(ctx.imageSmoothingQuality).toBe("high");
 expect(ctx.drawImage).toHaveBeenCalledTimes(1);
 expect(ctx.drawImage).toHaveBeenCalledWith(image,0,0,1020,1428);
 expect(ctx.restore).toHaveBeenCalled();
});
