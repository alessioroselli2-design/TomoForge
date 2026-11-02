// Shared gold frame; each category owns its internal composition.
 // A category may introduce interior artwork without replacing the outer master.
export const FRONT_OUTER_MASTER="/card-art/front-master-v17.webp";
export const CATEGORY_FRONT_LAYOUTS=Object.freeze({
 monster:{id:"monster-v17",interior:null,showDetails:true},
 class:{id:"class-v1",interior:"/card-art/class-interior-v17.webp",interiorY:740/1484,interiorHeight:661/1484,showDetails:false},
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
export const frontBackground=(type)=>{
 const layout=categoryFrontLayout(type);
 return {
  backgroundImage:`url(${FRONT_OUTER_MASTER})`,
  ...(layout.interior?{"--tf-class-background":`url(${layout.interior}),url(${FRONT_OUTER_MASTER})`}:{})
 };
};
