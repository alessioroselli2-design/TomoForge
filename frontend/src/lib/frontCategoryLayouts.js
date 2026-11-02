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
export const frontBackground=(type)=>{
 const layout=categoryFrontLayout(type);
 if(!layout.interior) return {backgroundImage:`url("${FRONT_OUTER_MASTER}")`};
 // Each layer's dimensions are relative to the same immutable full card.
 const position=layout.interiorY/(1-layout.interiorHeight)*100;
 return {
  backgroundImage:`url("${layout.interior}"),url("${FRONT_OUTER_MASTER}")`,
  backgroundSize:`100% ${(layout.interiorHeight*100).toFixed(5)}%,100% 100%`,
  backgroundPosition:`0 ${position.toFixed(5)}%,center center`,
  backgroundRepeat:"no-repeat,no-repeat",
 };
};
