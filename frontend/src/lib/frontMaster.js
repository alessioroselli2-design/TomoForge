// Ornate master recreated from the approved empty TomoForge card.
export const FRONT_MASTER_URL = "/card-art/front-master-v17.webp";
export const MASTER_REGIONS = Object.freeze({
 art:{x:18,y:72,w:304,h:117},
 badge:{x:286,y:40,r:28},emblem:{x:54,y:40,r:28},
 title:{x:170,y:29,w:146},subtitle:{x:170,y:54,w:146},
 stats:{y:195,h:42,x:18,w:304},abilities:{y:238,h:40,x:18,w:304},
 detail:{y:282,h:51,x:18,w:304},description:{y:335,h:112,x:18,w:304},
});

// Fractions of the 340 × 476 Monster master, shared by the DOM and print.
// A center at 9% keeps the topmost jewel of all 14 originals inside the trim.
const monsterEmblemWidth = 0.265;
export const MONSTER_EMBLEM_BOUNDS = Object.freeze({
  left: MASTER_REGIONS.emblem.x / 340 - monsterEmblemWidth / 2,
  top: 0.09 - (monsterEmblemWidth * 340 / 476) / 2,
  width: monsterEmblemWidth,
});

// Character shares the Monster well and exterior rail; retain the approved 26% class PNG.
export const CHARACTER_EMBLEM_BOUNDS = Object.freeze({
  left: MASTER_REGIONS.emblem.x / 340 - .26 / 2,
  top: .09 - (.26 * 340 / 476) / 2,
  width: .26,
});
