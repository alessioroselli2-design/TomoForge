// Shared gold frame; each category owns its internal composition.
 // A category may introduce interior artwork without replacing the outer master.
export const FRONT_OUTER_MASTER="/card-art/front-master-v17.webp";
export const CATEGORY_FRONT_LAYOUTS=Object.freeze({
 monster:{id:"monster-v17",interior:null,showDetails:true},
 class:{id:"class-5x7-finale",master:"/card-art/master-classe-5x7-senza-muscolo-e-anello-20261118.jpg",interior:null,showDetails:false},
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
// Versioned, restored copies of the nine approved masters. Originals remain
// the reference for trim geometry and can be recovered without any redraw.
export const restoredFrontMaster=src=>"/card-art/front-restored-v18/"+src.split("/").pop().replace(/\.(png|jpg|webp)$/i,".webp");
export const frontBackground=(type)=>({
 backgroundImage:`url(${restoredFrontMaster(categoryFrontLayout(type).master||FRONT_OUTER_MASTER)})`,
});
