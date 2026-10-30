// One high-resolution raster of the exact approved frame; never redraw the
// parchment or paste fragments on top of a different frame. Text and icons
// are added as independent dynamic layers by CardFront and print renderer.
export const FRONT_MASTER_URL = "/card-art/front-master-v7.webp";
// Pixel-level parchment restoration: the early master contained two hard-edged
// patches over the original labels. This transparent texture restores only
// those areas, with feathered edges; all frame filigree stays untouched.
export const FRONT_DETAIL_REPAIR_URL = "/card-art/front-detail-repair-v8.webp";
export const MASTER_REGIONS = Object.freeze({
  art: {x:18,y:76,w:304,h:125},
  badge:{x:285,y:39,r:31}, emblem:{x:55,y:39,r:30},
  title:{x:170,y:29,w:178}, subtitle:{x:170,y:54,w:178},
  stats:{y:208,h:41,x:18,w:304}, abilities:{y:252,h:42,x:18,w:304},
  detail:{y:295,h:53,x:18,w:304},
  description:{y:351,h:100,x:18,w:304},
});
