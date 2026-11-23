import React from "react";
import { getFrontEmblem } from "@/lib/frontEmblems";
import { raceCardView } from "@/lib/raceCardView";
import "./RaceCardFront.css";

const afterFrame=fn=>typeof requestAnimationFrame==="function"?requestAnimationFrame(fn):Promise.resolve().then(fn);
const cancelFrame=id=>typeof id==="number"&&typeof cancelAnimationFrame==="function"&&cancelAnimationFrame(id);
const fits=el=>el.scrollHeight<=el.clientHeight+1&&el.scrollWidth<=el.clientWidth+1;
// React owns the text nodes. Never replace textContent in a layout effect:
// subsequent edits in the real card editor can otherwise reconcile detached
// text nodes and crash the entire React tree (a black screen on mobile).
const useFit=(ref,value,{min=6,max=8.5,step=.5}={})=>{
 React.useLayoutEffect(()=>{
  const el=ref.current;if(!el)return;
  let active=true;let raf;
  const update=()=>{
   if(!active)return;
   cancelFrame(raf);
   raf=afterFrame(()=>{
    if(!active||!el.isConnected||!el.clientWidth||!el.clientHeight)return;
    // Always restart at the intended maximum on a new value or card size.
    // Only the CSS font size changes; the React-rendered text stays intact.
    for(let px=max;px>=min-.001;px-=step){
     el.style.fontSize=px+"px";
     if(fits(el))break;
    }
   });
  };
  update();
  document.fonts?.ready?.then(update);
  // Watching the parent avoids ResizeObserver loops caused by resizing the
  // text node itself while adapting font size in Safari/iOS.
  const resize=typeof ResizeObserver!=="undefined"?new ResizeObserver(update):null;
  resize?.observe(el.parentElement||el);
  return()=>{active=false;resize?.disconnect();cancelFrame(raf)};
 },[ref,value,min,max,step]);
};
const Fitted=({value,as:Tag="span",settings,className,...props})=>{
 const ref=React.useRef(null);
 useFit(ref,value,settings);
 return <Tag ref={ref} className={className} {...props}>{value}</Tag>;
};

// Measure actual multi-paragraph layout, not character counts. Only COMPLETE
// traits are retained, and font reduction happens before any trait is removed.
const useCompleteTraits=(ref,traits)=>{
 const [fit,setFit]=React.useState({size:11,count:traits.length});
 React.useLayoutEffect(()=>{
  const panel=ref.current;if(!panel)return;
  let active=true;let frame;
  const update=()=>{
   frame=afterFrame(()=>{
    if(!active||!panel.clientWidth||!panel.clientHeight)return;
    const probe=document.createElement("div");
    const computed=getComputedStyle(panel);
    Object.assign(probe.style,{
     position:"fixed",left:"-10000px",top:"0",visibility:"hidden",pointerEvents:"none",
     width:panel.clientWidth+"px",boxSizing:"border-box",fontFamily:computed.fontFamily,
     fontWeight:computed.fontWeight,lineHeight:"1.15",whiteSpace:"normal",overflowWrap:"break-word",
    });
    document.body.appendChild(probe);
    try{
     const nodes=traits.map(trait=>{
       const p=document.createElement("p");p.style.margin="0 0 2px";
       if(trait.name){const b=document.createElement("strong");b.textContent=trait.name+(/[.!?]$/.test(trait.name)?"":".");p.append(b);if(trait.description)p.append(document.createTextNode(" "));}
       p.append(document.createTextNode(trait.description||""));probe.append(p);return p;
     });
     let best={size:6.5,count:0};
     for(let size=11;size>=6.5-.01;size-=.5){
      probe.style.fontSize=size+"px";
      if(probe.scrollHeight<=panel.clientHeight+1){best={size,count:traits.length};break;}
     }
     if(best.count===0){
      probe.style.fontSize="6.5px";
      for(let count=traits.length;count>=0;count--){
       nodes.forEach((node,i)=>{node.style.display=i<count?"":"none"});
       if(probe.scrollHeight<=panel.clientHeight+1){best={size:6.5,count};break;}
      }
     }
     if(active)setFit(prev=>prev.size===best.size&&prev.count===best.count?prev:best);
    }finally{probe.remove()}
   });
  };
  update();document.fonts?.ready?.then(update);
  const observer=typeof ResizeObserver!=="undefined"?new ResizeObserver(update):null;
  observer?.observe(panel);
  return()=>{active=false;observer?.disconnect();if(typeof frame==="number"&&typeof cancelAnimationFrame==="function")cancelAnimationFrame(frame)};
 },[ref,traits]);
 return fit;
};
const Traits=({traits})=>{
 const ref=React.useRef(null);
 const fit=useCompleteTraits(ref,traits);
 return <div ref={ref} className="tf-race-traits" aria-label="Tratti razziali">
  <div className="tf-race-traits-inner" style={{fontSize:fit.size+"px"}}>
   {traits.slice(0,fit.count).map((trait,i)=><p key={i} className="tf-race-trait">
    {trait.name&&<><strong>{trait.name}{/[.!?]$/.test(trait.name)?"":"."}</strong>{trait.description&&" "}</>}
    {trait.description}
   </p>)}
  </div>
 </div>;
};
const COLS=[
 {field:"speed",start:6,end:34.7},
 {field:"darkvision",start:35.5,end:64.5},
 {field:"languages",start:65.3,end:94.9},
];
// A race-only safety boundary keeps the card editor usable if a future
// race record contains data that crashes this preview. Other card types are
// deliberately outside this boundary.
export class RaceCardErrorBoundary extends React.Component {
 constructor(props){super(props);this.state={hasError:false};}
 static getDerivedStateFromError(){return {hasError:true};}
 componentDidCatch(error){console.error("Errore nell'anteprima della carta Razza:",error);}
 render(){
  if(!this.state.hasError)return this.props.children;
  return <div data-front-category="race" className="tf-race-master"
   data-testid="race-preview-recovery"
   style={{backgroundImage:'url("/card-art/master-razze-5x7.png")'}}>
   <div style={{position:"absolute",left:"9%",top:"58%",width:"82%",
    textAlign:"center",fontSize:"12px",color:"#40210f",zIndex:10}}>
    Anteprima Razza momentaneamente non disponibile.
    Seleziona un altro tipo di carta e torna su Razza per riprovare.
   </div>
  </div>;
 }
}
export const RaceCardFront=React.forwardRef(({card={}},ref)=>{
 const view=React.useMemo(()=>raceCardView(card),[card]);
 const emblem=React.useMemo(()=>getFrontEmblem({...card,type:"race"}),[card]);
 return <div ref={ref} data-testid="card-front" data-front-version="7"
  data-front-category="race" data-front-layout="race-5x7-v1"
  className="tf-race-master" style={{backgroundImage:'url("/card-art/master-razze-5x7.png")'}}>
  <div className="tf-race-medallion" data-testid="front-emblem">
   {emblem?.src&&<img className="tf-race-emblem" src={emblem.src} alt={emblem.label||""} draggable={false}/>}
  </div>
  <header className="tf-race-heading">
   <Fitted as="h3" className="tf-race-title" value={view.name} title={view.name}
    settings={{min:6.5,max:21,step:.5}}/>
   <span className="tf-race-subtitle">Razza</span>
  </header>
  <div className="tf-race-size" aria-label={"Taglia: "+view.size}>
   <span>TAGLIA</span><Fitted as="strong" className="tf-race-size-value" value={view.size}
    settings={{min:6,max:13,step:.5}}/>
  </div>
  <div className="tf-race-illustration" aria-label="Finestra illustrazione vuota" />
  <section className="tf-race-stats" data-testid="race-stats" aria-label="Valori della razza">
   {COLS.map(col=><div key={col.field} data-race-field={col.field}
    className="tf-race-stat" style={{left:(col.start+8)+"%",width:(col.end-col.start-9.5)+"%"}}>
    <Fitted className="tf-race-stat-text" value={view[col.field]}
     title={view[col.field]} settings={{min:6,max:8.5,step:.5}}/>
   </div>)}
  </section>
  <Traits traits={view.traits}/>
  <section className="tf-race-lineages" aria-label="Sottorazze e lignaggi">
   {view.lineages&&<Fitted as="p" className="tf-race-lineages-text" value={view.lineages}
    title={view.lineages} settings={{min:6,max:9,step:.5}}/>}
  </section>
 </div>;
});
RaceCardFront.displayName="RaceCardFront";
