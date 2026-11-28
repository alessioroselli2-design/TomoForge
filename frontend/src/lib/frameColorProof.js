import { restoredFrontMaster } from "./frontCategoryLayouts";
import { frontMaskSource, getFrontExteriorMask, loadMaster, prepareNativeMaster, roundedTrimDistance } from "./frontExterior";
import palette from "./armorProofPalette.json";

export const ARMOR_METAL_LAYER = "/card-art/proofs/armor-metal-v25.webp";

export function bronzeTrimColor(r, g, b) {
  const light = .2126*r + .7152*g + .0722*b;
  const {knots, colors} = palette;
  let i = 0;
  while (i < knots.length-2 && light > knots[i+1]) i++;
  const f = (light-knots[i])/(knots[i+1]-knots[i]);
  return colors[i].map((v, k) => Math.round(v + f*(colors[i+1][k]-v)));
}

// The original trim already contains the silhouette, the two rails and the dark
// exterior fill. Change its metal profile, retaining the matte and every alpha.
function bronzeTrim(original) {
  const {width, height} = original;
  const trim = document.createElement("canvas");
  trim.width = width;
  trim.height = height;
  const ctx = trim.getContext("2d");
  ctx.drawImage(original, 0, 0);
  const pixels = ctx.getImageData(0, 0, width, height);
  const data = pixels.data;
  for (let i = 0; i < data.length; i += 4) {
    if (!data[i+3] || (data[i]===44 && data[i+1]===17 && data[i+2]===6)) continue;
    const pixel = i/4;
    const d = roundedTrimDistance(pixel%width, Math.floor(pixel/width), width, height);
    if (d >= 0 && d < Math.max(2,width*.009)) {
      data.set(bronzeTrimColor(data[i], data[i+1], data[i+2]), i);
    }
  }
  ctx.putImageData(pixels, 0, 0);
  trim.frameMeasurements = original.frameMeasurements;
  return trim;
}

export const METAL_PROOF_TYPES=Object.freeze(["monster","class","subclass","character","spell","feature","race","feat","item","weapon","armor"]);
export function metalProofUrl(type){
 if(!METAL_PROOF_TYPES.includes(type))throw new Error("Categoria di prova non supportata");
 if(type==="armor")return ARMOR_METAL_LAYER;
 // frontMaskSource is the authoritative master selection, including aliases.
 const name=restoredFrontMaster(frontMaskSource(type).src).split("/").pop();
 return "/card-art/proofs/metal-v26/"+name;
}
export async function getMetalProofLayers(type) {
  const [master, metal, exterior] = await Promise.all([
    loadMaster(restoredFrontMaster(frontMaskSource(type).src)),
    loadMaster(metalProofUrl(type)),
    getFrontExteriorMask(type),
  ]);
  if (!exterior || master.naturalWidth!==2040 || master.naturalHeight!==2856 ||
      metal.naturalWidth!==master.naturalWidth || metal.naturalHeight!==master.naturalHeight) {
    throw new Error("Master e maschera della categoria incompatibili");
  }
  return {
    type,
    background: prepareNativeMaster(master, exterior.bottomPlan, metal),
    trim: bronzeTrim(exterior),
  };
}

export const getArmorProofLayers=()=>getMetalProofLayers("armor");
// Undefined means the approved app finish. Null is the explicit original
// comparison selection. Non-canvas fixtures retain the original fallback.
export async function resolveFrontLayers(type, requested, canRender=true, load=getMetalProofLayers){
 if(requested!==undefined)return requested;
 return canRender&&METAL_PROOF_TYPES.includes(type)?load(type):null;
}
// One immutable background and trim URL per master category for the live UI.
// Keep the HD native canvas only during encoding, not in the preview cache.
const presentationCache=new Map();
const encodeCanvas=canvas=>new Promise((resolve,reject)=>{
 canvas.toBlob(blob=>blob?resolve(URL.createObjectURL(blob)):reject(new Error("Cornice non disponibile")),"image/png");
});
export function getMetalPresentation(type){
 if(!METAL_PROOF_TYPES.includes(type))return Promise.resolve(null);
 const key=metalProofUrl(type);
 if(!presentationCache.has(key)){
  const pending=getMetalProofLayers(type).then(async layers=>{
    const [background,src]=await Promise.all([encodeCanvas(layers.background),encodeCanvas(layers.trim)]);
    return {background,src};
  });
  presentationCache.set(key,pending);
  pending.catch(()=>presentationCache.delete(key));
 }
 return presentationCache.get(key);
}
