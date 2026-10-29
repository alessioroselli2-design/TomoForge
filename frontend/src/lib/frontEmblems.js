// Original approved TomoForge medals cropped from the user's final tables.
// One 44px-cell atlas keeps the iPhone editor quick to load.
const CLASSES = "barbaro,bardo,chierico,druido,guerriero,monaco,paladino,ranger,ladro,stregone,warlock,mago,artefice".split(",");
const MONSTERS = "aberrazione,bestia,celestiale,costrutto,drago,elementale,folletto,gigante,immondo,melma,mostruosita,non morto,pianta,umanoide".split(",");
const SCHOOLS = "abiurazione,ammaliamento,divinazione,evocazione,illusione,invocazione,necromanzia,trasmutazione".split(",");
const RACES = "umano,elfo,nano,halfling,gnomo,mezzelfo,mezzorco,dragonide,tiefling,aasimar,goliath,goblin,aarakocra,centauro,cangiante,coboldo,firbolg,forgiato,gith,kenku,orco,tortle,tritone,yuan-ti,genasi,tabaxi,leonin,minotauro,satiro,loxodon,vedalken,ibrido simic,morfico,kalashtar,verdan,hobgoblin,bugbear,lucertoloide,leporidion,owlin,fata,giff,plasmoide,thri-kreen,autognomo,kender,locathah,grung,dhampir,sangue strigo,rinato,hadozee".split(",");
const normalize = (v) => String(v || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
const ALIASES = {
  eladrin:"elfo",drow:"elfo","shadar kai":"elfo","elfo astrale":"elfo","elfo del mare":"elfo",
  duergar:"nano",svirfneblin:"gnomo","gnomo delle profondita":"gnomo",
  githyanki:"gith",githzerai:"gith",tortuga:"tortle","yuan ti sanguepuro":"yuan-ti",
  "orco di exandria":"orco","simic hybrid":"ibrido simic","shifter":"morfico",
  harengon:"leporidion",fairy:"fata",hexblood:"sangue strigo",reborn:"rinato",warforged:"forgiato",
  "lucertola umanoide":"lucertoloide","mezz orco":"mezzorco", "mezz elfo":"mezzelfo",
  "non morto":"non morto",undead:"non morto",aberration:"aberrazione",beast:"bestia",
  celestial:"celestiale",construct:"costrutto",dragon:"drago",elemental:"elementale",
  fey:"folletto",giant:"gigante",fiend:"immondo",ooze:"melma",monstrosity:"mostruosita",
  plant:"pianta",humanoid:"umanoide",wizard:"mago",cleric:"chierico",druid:"druido",
  fighter:"guerriero",rogue:"ladro",paladin:"paladino",barbarian:"barbaro",
  ranger:"ranger",bard:"bardo",sorcerer:"stregone",warlock:"warlock",artificer:"artefice",
  monk:"monaco", "evocation":"invocazione", "abjuration":"abiurazione",
  "conjuration":"evocazione","enchantment":"ammaliamento","illusion":"illusione",
  "divination":"divinazione","necromancy":"necromanzia","transmutation":"trasmutazione",
};
const keyFor = (value, keys) => {
 const normalized = normalize(value);
 if (!normalized) return null;
 const alias = ALIASES[normalized] || normalized;
 const exact = keys.indexOf(alias);
 if (exact >= 0) return exact;
 // Creature strings can include size or alignment. Prefer a matching whole type.
 return keys.findIndex(key => ((" "+alias+" ").includes(" "+key+" ")));
};
const site = "/emblemi/";
export const getFrontEmblem = (card = {}) => {
 const attrs = card.attributes || {};
 const type = card.type;
 let index = -1, sprite = "core", label = "";
 if (type === "monster") {
   label = attrs.tipo_creatura || attrs.tipo || attrs.creature_type || "";
   index = keyFor(label, MONSTERS);
   if (index >= 0) index += CLASSES.length;
 } else if (type === "spell") {
   label = attrs.scuola || attrs.school || "";
   index = keyFor(label, SCHOOLS);
   if (index >= 0) index += CLASSES.length + MONSTERS.length;
 } else if (type === "class" || type === "subclass" || type === "character") {
   label = type === "class" ? card.name : (attrs.classe || attrs.parent_class || "");
   index = keyFor(label, CLASSES);
 } else if (type === "feature") { index = 38; label = "Privilegi"; }
 else if (type === "feat") { index = 35; label = "Talenti"; }
 else if (type === "weapon" || type === "armor") { index = 36; label = "Armi e armature"; }
 else if (type === "item") { index = 37; label = "Oggetti magici"; }
 else if (type === "race") {
    sprite = "race";
    label = card.name || attrs.razza || "";
    index = keyFor(label, RACES);
 }
 if (index < 0) return null;
 const col = index % 8, row = Math.floor(index / 8);
 return {
   sprite, index, col, row, label,
   src: site + sprite + ".webp",
   width: 8 * 44, height: (sprite === "race" ? 7 : 5) * 44,
   cell: 44,
   backgroundPosition: `${(col / 7) * 100}% ${(row / (sprite === "race" ? 6 : 4)) * 100}%`,
   backgroundSize: `800% ${(sprite === "race" ? 700 : 500)}%`,
 };
};
