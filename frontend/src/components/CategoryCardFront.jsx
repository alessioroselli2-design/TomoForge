import React from "react";
import { artworkUrl } from "@/lib/api";
import { categoryCardView,completeUnits } from "@/lib/categoryCardView";
import "./CategoryCardFront.css";

const COLS=[{left:14,width:19.2},{left:43.5,width:19.5},{left:73.3,width:20.1}];
// React owns every text node. Only a detached measuring probe is modified.
// Reduce all text before dropping entire paragraphs/values, never clip a sentence.
function Fitted({value,units,as:Tag="div",className,min=6,max=8.5,lines,mode="text",...props}){
 const ref=React.useRef(null);
 const full=units?units.join("\n"):String(value??"");
 const [fit,setFit]=React.useState({source:full,text:full,size:max});
 React.useLayoutEffect(()=>{
  const el=ref.current;if(!el)return;
  let alive=true;
  let frame;
  const update=()=>{
   if(!alive)return;
   if(typeof frame==="number"&&typeof cancelAnimationFrame==="function")cancelAnimationFrame(frame);
   const measure=()=>{
    if(!alive||!el.clientWidth||!el.clientHeight)return;
    const css=getComputedStyle(el);
    const probe=document.createElement("div");
    Object.assign(probe.style,{position:"fixed",left:"-10000px",top:"0",visibility:"hidden",pointerEvents:"none",
      width:el.clientWidth+"px",boxSizing:"border-box",fontFamily:css.fontFamily,fontWeight:css.fontWeight,fontStyle:css.fontStyle,letterSpacing:css.letterSpacing,textTransform:css.textTransform,
      lineHeight:mode==="body"?"1.15":"1.1",whiteSpace:mode==="body"?"pre-line":"normal",overflowWrap:mode==="heading"?"normal":"anywhere",wordBreak:"normal",margin:"0",padding:"0"});
    document.body.appendChild(probe);
    try{
     const fits=(s,size,oneLine=false)=>{
      probe.style.fontSize=size+"px";
      probe.style.whiteSpace=oneLine?"nowrap":mode==="body"?"pre-line":"normal";
      probe.textContent=s;
      const limit=Math.min(el.clientHeight-(mode==="heading"?2:0),lines?lines*size*1.1+.5:el.clientHeight);
      return probe.getBoundingClientRect().height<=limit+.1&&probe.scrollWidth<=el.clientWidth;
     };
     let next={text:full,size:min};
     let found=false;
     if(mode==="heading"){
      for(let n=max;n>=Math.max(min,12)-.01;n-=.5){
       if(fits(full,n,true)){next={text:full,size:n};found=true;break;}
      }
     }
     if(!found)for(let n=max;n>=min-.01;n-=.5){if(fits(full,n)){next={text:full,size:n};found=true;break;}}
     if(!found){
      const entries=units||completeUnits(full);
      // For headings, try a smaller font, not a clipped name.
      if(mode==="heading"){
       for(let n=min-.5;n>=3;n-=.5){if(fits(full,n)){next={text:full,size:n};found=true;break;}}
      }
      if(!found){
       next={text:"",size:min};
       for(let count=entries.length;count>0;count--){
        const text=entries.slice(0,count).join(mode==="body"?"\n":" · ");
        if(fits(text,min)){next={text,size:min};break;}
       }
       // A single exceptionally long stat or note remains accessible in title.
       if(!next.text&&mode!=="body"&&full)next={text:"…",size:min};
      }
     }
     setFit(old=>old.source===full&&old.text===next.text&&old.size===next.size?old:{...next,source:full});
    }finally{probe.remove();}
   };
   if(typeof requestAnimationFrame==="function")frame=requestAnimationFrame(measure);else measure();
  };
  update();document.fonts?.ready?.then(update).catch(()=>{});
  const observer=typeof ResizeObserver==="function"?new ResizeObserver(update):null;
  observer?.observe(el);
  return()=>{alive=false;observer?.disconnect();if(typeof frame==="number"&&typeof cancelAnimationFrame==="function")cancelAnimationFrame(frame);};
 },[full,units,min,max,lines,mode]);
 const shown=fit.source===full?fit.text:full;
 return <Tag ref={ref} className={className} title={full} style={{fontSize:fit.size+"px"}} {...props}>{shown}</Tag>;
}
export const CategoryCardFront=React.forwardRef(({card={},imgUrl,exportMode},ref)=>{
 const view=React.useMemo(()=>categoryCardView(card),[card]);
 const src=imgUrl||(card.artwork_path?artworkUrl(card.artwork_path):"");
 const [failed,setFailed]=React.useState("");
 if(!view)return null;
 const {config}=view;
 return <div ref={ref} data-testid="card-front" data-front-version="7" data-front-category={card.type}
  data-front-layout={card.type+"-5x7-v1"} data-category-master="approved" className={"tf-category-master"+(exportMode?" tf-export-card":"")}
  style={{backgroundImage:"url('/card-art/"+config.master+"')"}}>
  <div className="tf-category-emblem" data-testid="front-emblem">
   <img src={"/emblemi/categorie/"+config.symbol} alt={"Emblema "+config.subtitle} draggable={false}/>
  </div>
  <header className="tf-category-heading">
   <Fitted as="h3" className="tf-category-name" value={view.name} mode="heading" min={6.5} max={20} lines={2}/>
   <Fitted as="p" className="tf-category-subtitle" value={view.subtitle} mode="heading" min={6} max={10} lines={1}/>
  </header>
  {view.badge&&<div className="tf-category-badge" aria-label={view.badgeLabel+" "+view.badge}>
   {view.badgeLabel&&<span>{view.badgeLabel}</span>}
   <Fitted as="strong" className="tf-category-badge-value" value={view.badge} min={6} max={13} lines={2}/>
  </div>}
  <section className="tf-category-artwork" aria-label="Illustrazione">
   {src&&failed!==src&&<img src={src} alt={view.name} crossOrigin="anonymous" draggable={false} onError={()=>setFailed(src)}/>}
  </section>
  <section className="tf-category-stats" aria-label="Valori della carta">
   {COLS.map((col,i)=><div className="tf-category-stat" key={config.fields[i]} style={{left:col.left+"%",width:col.width+"%"}}>
    <Fitted className="tf-category-stat-value" value={view.values[i]} aria-label={config.fields[i]} data-category-field={config.fields[i]} min={6} max={8.5} lines={3}/>
   </div>)}
  </section>
  <section className="tf-category-body" aria-label={config.section}>
   <Fitted className="tf-category-body-text" units={view.body.length?view.body:["—"]} mode="body" min={6.5} max={11}/>
  </section>
  <section className="tf-category-footer" aria-label={config.footer}>
   <Fitted className="tf-category-footer-text" value={view.footer} min={6} max={9} lines={2}/>
  </section>
 </div>;
});
CategoryCardFront.displayName="CategoryCardFront";
