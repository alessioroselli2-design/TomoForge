/**
 * Classe v49: one immutable, clean image for DOM, PNG and PDF.
 * The original JPG remains in the repository as an archival reference.
 * No browser inpainting, patch opacity, resized filigree, or detached footer.
 * The app overlays only the approved class emblem, v29 class die, and text.
 * Monster and all other categories are not processed here.
 */
export const CLASS_MASTER_SOURCE="/card-art/master-classe-pulito-v49.webp";
export const CLASS_MASTER_WIDTH=864;
export const CLASS_MASTER_HEIGHT=1210;
let prepared=null;
export const getPreparedClassMaster=()=>{
 if(prepared)return prepared;
 prepared=new Promise((resolve,reject)=>{
   const source=new Image();
   source.onload=()=>{
     try{
       const canvas=document.createElement("canvas");
       canvas.width=CLASS_MASTER_WIDTH;
       canvas.height=CLASS_MASTER_HEIGHT;
       const ctx=canvas.getContext("2d");
       if(!ctx)throw new Error("Canvas 2D unavailable");
       ctx.drawImage(source,0,0,CLASS_MASTER_WIDTH,CLASS_MASTER_HEIGHT);
       resolve({canvas,url:CLASS_MASTER_SOURCE});
     }catch(error){reject(error);}
   };
   source.onerror=()=>reject(new Error("Master Classe v49 non disponibile"));
   source.src=CLASS_MASTER_SOURCE;
   if(source.complete&&source.naturalWidth>0)source.onload();
 }).catch(err=>{prepared=null;throw err;});
 return prepared;
};
