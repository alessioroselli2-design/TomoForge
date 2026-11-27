import React from "react";
import jsPDF from "jspdf";
import { CardFront } from "@/components/TradingCard";
import { getCornerPreviewRadius } from "@/lib/pressGeometry";
import { PRESS_SPEC, addPressCardPages } from "@/lib/pressExport";
import { addSingleCardA4PdfPages, createCardPng, createCardBackPng } from "@/lib/cardExport";
import { getMetalProofLayers } from "@/lib/frameColorProof";

const SAMPLES=[
 {type:"monster",name:"Drago Rosso Adulto",attributes:{tipo_creatura:"Drago",taglia:"Enorme",allineamento:"Caotico Malvagio",grado_sfida:"17",classe_armatura:"19",punti_ferita:"256",velocita:"12 m",for:"27",des:"10",cos:"25",int:"16",sag:"13",car:"21"}},
 ...[["Aberrazione","Aboleth"],["Bestia","Lupo"],["Celestiale","Deva"],["Costrutto","Golem di Pietra"],["Elementale","Elementale del Fuoco"],["Folletto","Pixie"],["Gigante","Gigante delle Colline"],["Immondo","Balor"],["Melma","Cubo Gelatinoso"],["Mostruosità","Manticora"],["Non Morto","Scheletro"],["Pianta","Treant"],["Umanoide","Goblin"]].map(([tipo_creatura,name])=>({type:"monster",name,attributes:{tipo_creatura,taglia:"Media",grado_sfida:"1",classe_armatura:"12",punti_ferita:"10"}})),
 {type:"class",name:"Guerriero",attributes:{dado_vita:"d10",abilita_primaria:"Forza o Destrezza",tiri_salvezza:"Forza, Costituzione",competenze:"Armature e scudi"}},
 {type:"class",name:"Mago",attributes:{dado_vita:"d6",abilita_primaria:"Intelligenza",tiri_salvezza:"Intelligenza, Saggezza",competenze:"Armi semplici"}},
 {type:"class",name:"Druido",attributes:{dado_vita:"d8",abilita_primaria:"Saggezza",tiri_salvezza:"Intelligenza, Saggezza",competenze:"Armature leggere, scudi"}},
 {type:"subclass",name:"Circolo delle Stelle",attributes:{classe:"Druido"}},
 {type:"spell",name:"Palla di Fuoco",attributes:{livello:"3",scuola:"Invocazione",tempo_lancio:"1 azione",gittata:"45 m",danno:"8d6 fuoco"}},
 {type:"spell",name:"Benedizione",attributes:{livello:"1",scuola:"Ammaliamento",tempo_lancio:"1 azione",gittata:"9 m",durata:"Concentrazione, fino a 1 minuto",componenti:"V, S, M"}},
 {type:"spell",name:"Scudo",attributes:{livello:"1",scuola:"Abiurazione",tempo_lancio:"1 reazione",gittata:"Personale",durata:"1 round",componenti:"V, S"}},
 {type:"spell",name:"Animare Morti",attributes:{livello:"3",scuola:"Necromanzia",tempo_lancio:"1 minuto",gittata:"3 m",durata:"Istantanea",componenti:"V, S, M"}},
 {type:"race",name:"Elfo",attributes:{taglia:"Media",velocita:"9 m"}},
 {type:"feature",name:"Forma Selvatica",attributes:{classe:"Druido",livello:"2"}},
 {type:"feat",name:"Maestro d'Armi",attributes:{bonus_caratteristica:"+1 Forza o Destrezza"}},
 {type:"item",name:"Spada del Sole della Fiamma Eterna",attributes:{tipo:"Arma",rarita:"Molto raro"}},
 {type:"item",name:"Bastone dei Boschi",attributes:{tipo:"Bastone",rarita:"Raro"}},
 {type:"weapon",name:"Spada Lunga",attributes:{danno:"1d8",tipo_danno:"Tagliente",proprieta:"Versatile (1d10)"}},
 {type:"armor",name:"Cotta di Maglia",attributes:{categoria_armatura:"pesante",classe_armatura:"16"}},
 {type:"character",name:"Personaggio · Luce",back:{variant:"luminous"},attributes:{classe:"Druido",livello:"5"}},
 {type:"character",name:"Personaggio · Argento",back:{variant:"silver"},attributes:{classe:"Druido",livello:"5"}},
];
function FaceZoom({face,onClose}) {
 const modal=React.useRef(null);
 const [scale,setScale]=React.useState(0);
 React.useEffect(()=>{
  modal.current.showModal();
 },[]);
 const control="border border-gold-deep rounded px-3 py-2";
 return <dialog ref={modal} onClose={onClose} aria-label={face.label}
  className="bg-obsidian text-foreground border border-gold-deep p-3 rounded"
  style={{width:"min(96vw, 1120px)",maxWidth:"96vw",maxHeight:"95dvh"}}>
  <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
   <strong>{face.label}</strong>
   <div className="flex gap-1">
    {[[0,"Adatta"],[1,"100%"],[2,"200%"]].map(([value,label])=>
     <button key={value} className={control} aria-pressed={scale===value} onClick={()=>setScale(value)}>{label}</button>)}
    <button className={control} onClick={()=>modal.current.close()}>Chiudi</button>
   </div>
  </div>
  <div style={{maxHeight:"76dvh",overflow:"auto",overscrollBehavior:"contain"}}>
   <img src={face.src} alt={face.label} style={scale?
    {display:"block",width:1020*scale,maxWidth:"none",height:"auto"}:
    {display:"block",maxWidth:"100%",maxHeight:"75dvh",margin:"auto"}}/>
  </div>
 </dialog>;
}

export default function PrintPressPreview(){
 const [index,setIndex]=React.useState(()=>SAMPLES.findIndex(s=>s.name==="Cotta di Maglia"));
 const [busy,setBusy]=React.useState(false);
 const [feedback,setFeedback]=React.useState("");
 const [proof,setProof]=React.useState(null);
 const [rounded,setRounded]=React.useState(true);
 const [matched,setMatched]=React.useState(true);
 const [zoom,setZoom]=React.useState(null);
 const previewStyle={width:"100%",aspectRatio:"5/7",overflow:"hidden",borderRadius:rounded?getCornerPreviewRadius():0};
 const ref=React.useRef(null);
 const card=React.useMemo(()=>({...SAMPLES[index],description:"Carta dimostrativa per il confronto del fronte e del retro. Nessun dato viene salvato."}),[index]);
 React.useEffect(()=>{
  let active=true;setProof(null);
  (async()=>{
   try{
    const front=await createCardPng(ref.current,card);
    if(!active)return;
    const back=await createCardBackPng(card);
    if(!active)return;
    const original={front:front.toDataURL("image/png"),back:back.toDataURL("image/png"),frontW:front.width,frontH:front.height,backW:back.width,backH:back.height,frame:front.frameMeasurements,heading:front.exportHeading,badge:front.exportBadge};
    {
     try{
      const layers=await getMetalProofLayers(card.type);
      if(!active)return;
      const variant=await createCardPng(ref.current,card,layers);
      if(active)setProof({...original,layers,matched:variant.toDataURL("image/png")});
     }catch(error){
      if(active){
       setMatched(false);setProof(original);
       setFeedback("Disponibile il fronte originale. Errore nella prova brunita: "+error.message);
      }
     }
    }
   }catch(error){if(active)setFeedback("Anteprima non disponibile: "+(error?.message||"riprova"));}
  })();
  return()=>{active=false;};
 },[card]);
 const selectedLayers=matched?proof?.layers:undefined;
 const variantName=selectedLayers?"oro-brunito":"v18";
 const faces=proof?[
  {label:"Fronte originale · v18",src:proof.front},
  ...(proof.matched?[{label:"Fronte · oro brunito",src:proof.matched}]:[]),
  {label:"Retro approvato",src:proof.back},
 ]:[];
 async function download(press){
  if(!ref.current||busy)return;
  setBusy(true);setFeedback("Preparazione del PDF…");
  try{
   const format=press?[PRESS_SPEC.pageWidth,PRESS_SPEC.pageHeight]:"a4";
   const pdf=new jsPDF({orientation:"portrait",unit:"mm",format,compress:true});
   if(press)await addPressCardPages(pdf,ref.current,card,{frontLayers:selectedLayers});
   else await addSingleCardA4PdfPages(pdf,ref.current,card,selectedLayers);
   pdf.save("tomeforge-prova-"+(press?"tipografia":"a4")+"-"+card.type+"-"+variantName+".pdf");
   setFeedback("PDF generato. Aprilo da File e controlla entrambe le pagine.");
  }catch(error){setFeedback("Errore di esportazione: "+(error?.message||"riprova"));}
  finally{setBusy(false);}
 }
 async function downloadPng(back){
  if(!ref.current||busy)return;
  setBusy(true);setFeedback("Preparazione PNG…");
  try{
   const url=back?proof.back:(selectedLayers?proof.matched:proof.front);
   const link=document.createElement("a");
   link.download="tomeforge-prova-"+card.type+"-"+(back?"retro":"fronte-"+variantName)+".png";
   link.href=url;link.click();
   setFeedback("PNG generato.");
  }catch(error){setFeedback("Errore PNG: "+(error?.message||"riprova"));}
  finally{setBusy(false);}
 }
 return <main className="min-h-screen bg-obsidian text-gold px-3 py-6 text-center" data-testid="print-press-preview">
  <div className="max-w-6xl mx-auto">
   <h1 className="font-display text-2xl">TomoForge · Collaudo stampa · revisione 26</h1>
   <p className="my-3 text-sm">Confronto oro brunito su tutte le categorie. Tocca una carta per ingrandirla e controllare i dettagli. Editor e produzione invariati.</p>
   <label className="block my-4 text-sm">Scegli una carta
    <select disabled={busy} value={index} onChange={e=>{setProof(null);setIndex(Number(e.target.value));setFeedback("");}} className="block mx-auto mt-2 p-2 border border-gold-deep bg-card text-foreground">
     {SAMPLES.map((s,i)=><option key={i} value={i}>{s.name}</option>)}
    </select>
   </label>
   <label className="flex items-center justify-center gap-2 my-3 text-xs">
    <input type="checkbox" checked={rounded} onChange={e=>setRounded(e.target.checked)} data-testid="rounded-corners-toggle"/>
    Simula il taglio arrotondato (R 3 mm)
   </label>
   <div className={"grid grid-cols-2 gap-3 mx-auto "+(faces.length===3?"md:grid-cols-3":"max-w-[690px]")}>
    {faces.map(face=><figure key={face.label} className="min-w-0">
     <figcaption className="text-sm mb-2">{face.label}</figcaption>
     <button type="button" aria-label={"Ingrandisci "+face.label} onClick={()=>setZoom(face)}
      style={{...previewStyle,display:"block",cursor:"zoom-in"}}>
      <img src={face.src} alt={face.label} className="block w-full h-full"/>
     </button>
    </figure>)}
   </div>
   {!proof&&!feedback&&<p role="status" className="my-4">Preparazione delle carte…</p>}
   {zoom&&<FaceZoom face={zoom} onClose={()=>setZoom(null)}/>}
   {proof&&<p className="mt-3 text-xs" data-testid="proof-dimensions">
    Fronte: {proof.frontW} × {proof.frontH} px · Retro: {proof.backW} × {proof.backH} px
    {proof.frontW===proof.backW&&proof.frontH===proof.backH?" · Misure identiche":" · ATTENZIONE: misure diverse"}
   </p>}
   {proof?.heading&&<p className="mt-2 text-xs" data-testid="export-heading-proof">Titolo rasterizzato: {proof.heading.title} · {proof.heading.subtitle}</p>}
   {proof?.badge&&<p className="mt-2 text-xs" data-testid="export-badge-proof">Medaglione rasterizzato: {proof.badge.label} {proof.badge.value}</p>}
   {proof?.frame&&<div className="mt-4 text-xs" data-testid="ornamental-frame-measurements">
    <p className="font-semibold">Distanza del fregio originale dal taglio (mm)</p>
    <div className="overflow-x-auto"><table className="mx-auto mt-2 text-left"><thead><tr><th className="p-1">Lato</th><th className="p-1">Prima</th><th className="p-1">Ora</th><th className="p-1">Mostro</th></tr></thead><tbody>
    {["top","bottom","left","right"].map((side,i)=>{
      const mm=v=>v===null||v===undefined?"—":(v*(i<2?88.9/proof.frame.height:63.5/proof.frame.width)).toFixed(2).replace(".",",");
      return <tr key={side}><th className="p-1">{["Alto","Basso","Sinistra","Destra"][i]}</th><td className="p-1">{mm(proof.frame.before[side])}</td><td className="p-1">{mm(proof.frame.after[side])}</td><td className="p-1">{mm(proof.frame.reference[side])}</td></tr>;
    })}
    </tbody></table></div>
    <p className="mt-2">Misura del tratto dorato rettilineo, non del filetto aggiunto. Gemme inferiori spostate intere, senza ingrandimento.</p>
   </div>}
   {proof?.matched&&<fieldset className="mt-6">
    <legend className="mx-auto text-sm mb-2">Fronte da esportare in PNG e PDF</legend>
    {[["Originale v18",false],["Oro brunito",true]].map(([label,value])=>
     <label key={label} className="mx-2 inline-flex items-center gap-2 text-sm">
      <input type="radio" name="export-finish" checked={matched===value} disabled={busy} onChange={()=>setMatched(value)}/>{label}
     </label>)}
   </fieldset>}
   <div className="flex flex-wrap justify-center gap-3 mt-6">
    <button disabled={busy||!proof} onClick={()=>download(true)} className="border border-gold bg-gold text-obsidian px-4 py-3 text-sm">SCARICA PDF TIPOGRAFIA</button>
    <button disabled={busy||!proof} onClick={()=>download(false)} className="border border-gold px-4 py-3 text-sm">SCARICA PDF A4 FRONTE/RETRO</button>
    <button disabled={busy||!proof} onClick={()=>downloadPng(false)} className="border border-gold px-4 py-3 text-sm">PNG FRONTE</button>
    <button disabled={busy||!proof} onClick={()=>downloadPng(true)} className="border border-gold px-4 py-3 text-sm">PNG RETRO</button>
   </div>
   <p role="status" className="mt-3 text-sm">{feedback}</p>
   <p className="mt-3 text-xs text-foreground/70">PDF tipografia: taglio 63,5 × 88,9 mm, 3 mm abbondanza, raggio angoli richiesto 3 mm. Il PDF conserva la grafica rettangolare completa per la fustellatura. PDF A4: due pagine sovrapponibili sullo stesso foglio, riferimenti esterni da 1,05 mm. Nelle opzioni stampante scegliere fronte/retro, lato lungo e 100% (senza adattamento); arrotondare dopo il taglio con una fustella R 3 mm.</p>
   <div aria-hidden="true" style={{position:"fixed",left:-99999,top:0,width:340,height:476}} ref={ref}><CardFront card={card} exportMode/></div>
  </div>
 </main>;
}
