import fs from "fs";
import path from "path";
import crypto from "crypto";
const assets=[
  [
    "public/card-art/master-talento-5x7.png",
    "5f6f8397c4364df55606b02b5ba7fa6052ae8546"
  ],
  [
    "public/card-art/master-oggetto-magico-5x7.png",
    "1bedebb23bb784573b77b8d957adadb3c4f55903"
  ],
  [
    "public/card-art/master-arma-5x7.png",
    "c7e61138cb7ed9aff6699e74b59fc8aa843f0ebb"
  ],
  [
    "public/card-art/master-armatura-5x7.png",
    "b0d0d54624b7d3eb1c89bd4587b09ca12f749a68"
  ],
  [
    "public/emblemi/categorie/simbolo-talenti.png",
    "e2545b5d37cc085a2e1ef17327f9e14efeac6864"
  ],
  [
    "public/emblemi/categorie/simbolo-oggetti-magici.png",
    "4cf79c23ce18c64c395056c2cb0764f9cdfc2156"
  ],
  [
    "public/emblemi/categorie/simbolo-armi-armature.png",
    "e3c1ef80c024795319f85300d67daf22667d29a6"
  ]
];
test.each(assets)("%s is exactly the approved PNG",(file,hash)=>{
 const bytes=fs.readFileSync(path.resolve(process.cwd(),file));
 const gitHash=crypto.createHash("sha1").update(Buffer.from("blob "+bytes.length+"\0")).update(bytes).digest("hex");
 expect(gitHash).toBe(hash);
 const isSymbol=file.startsWith("public/emblemi/");
 expect(bytes.readUInt32BE(16)).toBe(isSymbol?640:1024);
 expect(bytes.readUInt32BE(20)).toBe(isSymbol?640:1434);
});
