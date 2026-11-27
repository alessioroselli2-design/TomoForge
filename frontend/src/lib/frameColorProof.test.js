import fs from "fs";
import path from "path";
import {BRONZE_MASTER_URL,bronzeTrimColor} from "./frameColorProof";
test("standalone proof artwork is a full-size lossless WebP",()=>{
 const b=fs.readFileSync(path.resolve(process.cwd(),"public"+BRONZE_MASTER_URL));
 expect(b.toString("ascii",0,4)).toBe("RIFF");
 expect(b.toString("ascii",8,16)).toBe("WEBPVP8L");
 const packed=b.readUInt32LE(21);
 expect((packed&16383)+1).toBe(2040);
 expect(((packed>>>14)&16383)+1).toBe(2856);
});
test("synthetic trim maps continuously from black to warm bronze",()=>{
 expect(bronzeTrimColor(0,0,0)).toEqual([0,0,0]);
 expect(bronzeTrimColor(255,255,255)).toEqual([250,201,119]);
 const a=bronzeTrimColor(180,180,180);
 expect(a).toEqual([203,133,53]);
});
