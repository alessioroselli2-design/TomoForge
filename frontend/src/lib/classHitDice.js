// A single high-resolution jewel family for every valid class Hit Die.
// Use the verified class record instead of guessing by class name.
export const CLASS_HIT_DICE = Object.freeze(["d4","d6","d8","d10","d12","d20"]);

export const normalizeClassHitDie = (value) => {
  const match=String(value??"").trim().match(/^(?:1\s*)?d\s*(4|6|8|10|12|20)$/i);
  return match ? `d${match[1]}` : "";
};

export const classHitDieAsset = (value) => {
  const die=normalizeClassHitDie(value);
  return die ? `/card-art/class-dice/${die}-gem-v27.svg` : "";
};
