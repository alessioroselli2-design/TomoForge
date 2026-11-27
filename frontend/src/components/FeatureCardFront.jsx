import React from "react";
import {artworkUrl} from "@/lib/api";
import {getFrontEmblem} from "@/lib/frontEmblems";
import {buildFeatureCardView,featureSentences} from "@/lib/featureCardView";
import "./FeatureCardFront.css";

const STAT_COLUMNS=[
 {key:"activation",left:13.8,width:19.4},
 {key:"uses",left:43.5,width:19.5},
 {key:"recovery",left:73.3,width:20.3},
];
const delayFrame=fn=>typeof requestAnimationFrame==="function"?
 requestAnimationFrame(fn):Promise.resolve().then(fn);
const cancelFrame=id=>typeof id==="number"&&typeof cancelAnimationFrame==="function"&&cancelAnimationFrame(id);
const textFits=el=>el.scrollHeight<=el.clientHeight+1 && el.scrollWidth<=el.clientWidth+1;
const measureText=(el,value,{min=6,max=10,step=.5,completeSentences=false}={})=>{
 if(!el)return;
 const source=String(value||"").replace(/\s+/g," ").trim();
 if(!source){el.textContent="";return;}
 el.textContent=source;
 if(el.clientHeight===0||el.clientWidth===0)return; // jsdom / hidden tab
 for(let size=max;size>=min-.01;size-=step){
  el.style.fontSize=size+"px";
  el.textContent=source;
  if(textFits(el))return;
 }
 el.style.fontSize=min+"px";
 if(completeSentences){
  // Trim one complete sentence at a time, preserving the entire original
  // in card data rather than leaving a dangling fragment on the printout.
  const candidates=featureSentences(source);
  for(let i=candidates.length-1;i>=0;i--){
   el.textContent=candidates[i];
   if(textFits(el))return;
  }
  el.textContent="";return;
 }
 if(!textFits(el)){
  // For single-line headings and short stat fields preserve a stable
  // non-overflowing view even when the source is unusually long.
  el.textContent=source;
 }
};
const useFittedText=(ref,value,settings)=>{
 const config=React.useRef(settings);
 config.current=settings;
 React.useLayoutEffect(()=>{
  const element=ref.current;if(!element)return;
  let cancelled=false;
  let frame;
  const apply=()=>{if(!cancelled)frame=delayFrame(()=>{if(!cancelled)measureText(element,value,config.current)})};
  apply();
  if(typeof document!=="undefined"&&document.fonts?.ready){
   Promise.resolve(document.fonts.ready).then(apply);
  }
  if(typeof ResizeObserver!=="undefined"){
   const obs=new ResizeObserver(apply);obs.observe(element);
   return ()=>{cancelled=true;obs.disconnect();cancelFrame(frame)};
  }
  return ()=>{cancelled=true;cancelFrame(frame)};
 },[ref,value]);
};
const FittedText=({as:Tag="span",value,settings,className,children,...props})=>{
 const ref=React.useRef(null);
 useFittedText(ref,value,settings);
 return <Tag ref={ref} className={className} {...props}>{children??value}</Tag>;
};
export const FeatureCardFront=React.forwardRef(
 ({card={},imgUrl,exportMode},ref)=>{
  const view=buildFeatureCardView(card);
  const emblem=getFrontEmblem({...card,type:"feature"});
  const src=imgUrl||(card.artwork_path?artworkUrl(card.artwork_path):"");
  const [artError,setArtError]=React.useState(false);
  React.useEffect(()=>setArtError(false),[src]);
  return <div ref={ref} data-testid="card-front" data-front-version="7"
   data-front-category="feature" data-front-layout="feature-5x7-v5"
   className={"tf-feature-master"+(exportMode?" tf-export-card":"")} style={{backgroundImage:'url("/card-art/front-restored-v18/master-privilegi-5x7.webp")'}}>
   <div className="tf-feature-medallion" data-testid="front-emblem">
    {emblem&&<img className="tf-feature-original-emblem" src={emblem.src}
      alt="Emblema dei privilegi" draggable={false}/>}
   </div>
   <header className="tf-feature-heading">
    <FittedText as="h3" className="tf-feature-title" value={view.name}
      settings={{max:21,min:6.5,step:.5}} title={view.name}/>
    <FittedText as="p" className="tf-feature-subtitle" value={view.subtitle}
      settings={{max:10,min:6.5,step:.5}} title={view.subtitle}/>
   </header>
   {view.level&&<div className="tf-feature-level" aria-label={"Livello "+view.level}>
    <strong>{view.level}</strong><span>LIV.</span>
   </div>}
   <section className="tf-feature-artwork" aria-label="Illustrazione del privilegio">
    {src&&!artError&&<img src={src} data-artwork-src={src} alt={view.name}
      crossOrigin="anonymous" draggable={false} onError={()=>setArtError(true)}/>}
   </section>
   <section className="tf-feature-stats" data-testid="feature-stats" aria-label="Valori del privilegio">
    {STAT_COLUMNS.map(({key,left,width})=><div key={key}
     className="tf-feature-stat-value" data-feature-field={key}
     style={{left:left+"%",width:width+"%"}}>
     <FittedText as="span" className="tf-feature-stat-text"
      value={view[key]||"—"} title={view[key]||"—"}
      settings={{max:8.5,min:6,step:.5}}/>
    </div>)}
   </section>
   <section className="tf-feature-description-area" aria-label="Descrizione del privilegio">
    <FittedText as="p" className="tf-feature-description" value={view.displayDescription}
     title={view.description} settings={{max:11,min:6.5,step:.5,completeSentences:true}}/>
   </section>
   <section className="tf-feature-progression" data-testid="feature-progression"
     aria-label="Progressione del privilegio">
     {view.progression&&<FittedText as="p" className="tf-feature-progression-text"
       value={view.progression} title={view.progression}
       settings={{max:10,min:6,step:.5}}/>}
   </section>
  </div>;
 });
FeatureCardFront.displayName="FeatureCardFront";
