// Shared gold frame; each category owns its internal composition.
 // A category may introduce interior artwork without replacing the outer master.
export const FRONT_OUTER_MASTER="/card-art/front-master-v17.webp";
export const CATEGORY_FRONT_LAYOUTS=Object.freeze({
 monster:{id:"monster-v17",interior:null,showDetails:true},
 class:{id:"class-user-original-1024x1536",master:"/card-art/references/approved-class-master-864x1210.webp",interior:null,showDetails:false},
 spell:{id:"spell-v17",interior:null,showDetails:true},
 subclass:{id:"subclass-v17",interior:null,showDetails:true},
 feature:{id:"feature-v17",interior:null,showDetails:true},
 race:{id:"race-v17",interior:null,showDetails:true},
 feat:{id:"feat-v17",interior:null,showDetails:true},
 weapon:{id:"weapon-v17",interior:null,showDetails:true},
 armor:{id:"armor-v17",interior:null,showDetails:true},
 item:{id:"item-v17",interior:null,showDetails:true},
 character:{id:"character-v17",interior:null,showDetails:true},
 custom:{id:"custom-v17",interior:null,showDetails:true},
});
export const categoryFrontLayout=(type)=>CATEGORY_FRONT_LAYOUTS[type]||CATEGORY_FRONT_LAYOUTS.custom;
// The outer reference stays the same inline style for EVERY category.
// Inner background layers are owned by each category CSS (not by the shell).
// One self-contained raster for each category. No layered pasted rectangles.
// A single historical master has no lower-right gold die ring.
export const frontMasterAsset=(type)=>categoryFrontLayout(type).master||FRONT_OUTER_MASTER;
export const frontBackground=(type,emblem=null,dice="")=>({
 backgroundImage:`url(${frontMasterAsset(type)})`,
});
