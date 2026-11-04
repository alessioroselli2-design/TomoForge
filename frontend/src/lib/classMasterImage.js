/**
 * A single, dynamically prepared Class background for screen and print.
 * The SOURCE stays the user's exact approved JPG. This operation does not
 * redraw ornaments or touch other card categories.
 *
 * 1. A parchment sample from the original fills the baked-in die well.
 *    The app draws ONE full class-specific die in that empty well.
 * 2. The lower parchment is extended while moving the complete original
 *    terminal border flush to y=1210. The detached flourish below is omitted.
 * 3. The upper-left and upper-right wells remain exactly as approved.
 */
export const CLASS_MASTER_SOURCE = "/card-art/class-master-user-final-20261103.jpg";
export const CLASS_MASTER_WIDTH = 864;
export const CLASS_MASTER_HEIGHT = 1210;

let prepared = null;

export const getPreparedClassMaster = () => {
 if (prepared) return prepared;
 prepared = new Promise((resolve,reject) => {
   const source = new Image();
   source.onload = () => {
     try {
       const w=CLASS_MASTER_WIDTH,h=CLASS_MASTER_HEIGHT;
       const scratch=document.createElement("canvas");
       scratch.width=w;scratch.height=h;
       const sc=scratch.getContext("2d",{willReadFrequently:true});
       if(!sc)throw new Error("Canvas 2D unavailable");
       sc.drawImage(source,0,0,w,h);
       const pixels=sc.getImageData(0,0,w,h);
       const original=new Uint8ClampedArray(pixels.data);
       const output=pixels.data;
       // Copy only plain parchment from the left side of the same lower well.
       // Smooth elliptical feather covers the entire original die and its ring.
       const left=606,top=799,sw=240,sh=252,sourceLeft=360;
       for(let y=0;y<sh;y++){
         for(let x=0;x<sw;x++){
           const dx=(x-120)/119,dy=(y-126)/123;
           const dist=Math.sqrt(dx*dx+dy*dy);
           if(dist>=1)continue;
           const t=dist<=.85?1:(1-dist)/.15;
           const alpha=t*t*(3-2*t);
           const i=((top+y)*w+(left+x))*4;
           const j=((top+y)*w+(sourceLeft+x))*4;
           for(let c=0;c<3;c++) output[i+c]=Math.round(original[i+c]*(1-alpha)+original[j+c]*alpha);
         }
       }
       sc.putImageData(pixels,0,0);
       const clean=document.createElement("canvas");
       clean.width=w;clean.height=h;
       const ctx=clean.getContext("2d");
       if(!ctx)throw new Error("Canvas 2D unavailable");
       ctx.drawImage(scratch,0,0,w,990,0,0,w,990);
       // Extend ONLY undecorated lower parchment; don't scale the gold frame.
       ctx.drawImage(scratch,0,990,w,110,0,990,w,170);
       // Preserve the complete final filigree, positioned flush with the edge.
       ctx.drawImage(scratch,0,1100,w,50,0,1160,w,50);
       resolve({canvas:clean,url:clean.toDataURL("image/webp",.96)});
     } catch(error){reject(error);}
   };
   source.onerror=()=>reject(new Error("Immagine master Classe non disponibile"));
   source.src=CLASS_MASTER_SOURCE;
   if(source.complete&&source.naturalWidth>0)source.onload();
 }).catch(error=>{prepared=null;throw error;});
 return prepared;
};
