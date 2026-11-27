import React from "react";
import jsPDF from "jspdf";
import { CardFront } from "@/components/TradingCard";
import { getCornerPreviewRadius } from "@/lib/pressGeometry";
import { PRESS_SPEC, addPressCardPages } from "@/lib/pressExport";
import { addSingleCardA4PdfPages, createCardPng, createCardBackPng } from "@/lib/cardExport";
import { createFrameColorProof } from "@/lib/frameColorProof";

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
export default function PrintPressPreview(){
 const [index,setIndex]=React.useState(()=>SAMPLES.findIndex(s=>s.name==="Cotta di Maglia"));
 const [busy,setBusy]=React.useState(false);
 const [feedback,setFeedback]=React.useState("");
 const [proof,setProof]=React.useState(null);
 const [rounded,setRounded]=React.useState(true);
 const [matched,setMatched]=React.useState(true);
 const previewStyle={width:"100%",aspectRatio:"5/7",overflow:"hidden",borderRadius:rounded?getCornerPreviewRadius():0};
 const ref=React.useRef(null);
 const card=React.useMemo(()=>({...SAMPLES[index],description:"Carta dimostrativa per il confronto del fronte e del retro. Nessun dato viene salvato."}),[index]);
 React.useEffect(()=>{
  let active=true;setProof(null);
  (async()=>{
   try{
    const front=await createCardPng(ref.current,card);
    const back=await createCardBackPng(card);
    if(!active)return;
    const variant=card.name==="Cotta di Maglia"?await createFrameColorProof(front,back):null;
    if(active)setProof({matched:variant?.canvas.toDataURL("image/png"),color:variant?.color,changed:variant?.changed,front:front.toDataURL("image/png"),back:back.toDataURL("image/png"),frontW:front.width,frontH:front.height,backW:back.width,backH:back.height,frame:front.frameMeasurements,heading:front.exportHeading,badge:front.exportBadge});
   }catch(error){if(active)setFeedback("Anteprima non disponibile: "+(error?.message||"riprova"));}
  })();
  return()=>{active=false;};
 },[card]);
 async function download(press){
  if(!ref.current||busy)return;
  setBusy(true);setFeedback("Preparazione del PDF…");
  try{
   const format=press?[PRESS_SPEC.pageWidth,PRESS_SPEC.pageHeight]:"a4";
   const pdf=new jsPDF({orientation:"portrait",unit:"mm",format,compress:true});
   if(press)await addPressCardPages(pdf,ref.current,card);
   else await addSingleCardA4PdfPages(pdf,ref.current,card);
   pdf.save("tomeforge-prova-"+(press?"tipografia":"a4")+"-"+card.type+".pdf");
   setFeedback("PDF generato. Aprilo da File e controlla entrambe le pagine.");
  }catch(error){setFeedback("Errore di esportazione: "+(error?.message||"riprova"));}
  finally{setBusy(false);}
 }
 async function downloadPng(back){
  if(!ref.current||busy)return;
  setBusy(true);setFeedback("Preparazione PNG…");
  try{
   const canvas=back?await createCardBackPng(card):await createCardPng(ref.current,card);
   const link=document.createElement("a");
   link.download="tomeforge-prova-"+card.type+"-"+(back?"retro":"fronte")+".png";
   link.href=canvas.toDataURL("image/png");link.click();
   setFeedback("PNG generato.");
  }catch(error){setFeedback("Errore PNG: "+(error?.message||"riprova"));}
  finally{setBusy(false);}
 }
 return <main className="min-h-screen bg-obsidian text-gold px-3 py-6 text-center" data-testid="print-press-preview">
  <div className="max-w-3xl mx-auto">
   <h1 className="font-display text-2xl">TomoForge · Collaudo stampa</h1>
   <p className="my-3 text-xs text-foreground/75">Anteprima PR #704 · revisione 22 · maschera della pergamena e metallo brunito (Cotta di Maglia) · stampa A4 fronte/retro · renderer reale · nessun login, nessuna modifica alla collezione.</p>
   <label className="block my-4 text-sm">Scegli una carta
    <select disabled={busy} value={index} onChange={e=>{setIndex(Number(e.target.value));setFeedback("");}} className="block mx-auto mt-2 p-2 border border-gold-deep bg-card text-foreground">
     {SAMPLES.map((s,i)=><option key={i} value={i}>{s.name}</option>)}
    </select>
   </label>
   <label className="flex items-center justify-center gap-2 my-3 text-xs">
    <input type="checkbox" checked={rounded} onChange={e=>setRounded(e.target.checked)} data-testid="rounded-corners-toggle"/>
    Simula il taglio arrotondato (R 3 mm)
   </label>
   {card.name==="Cotta di Maglia"&&<div className="my-4 p-3 border border-gold-deep rounded text-sm">
    <p className="font-semibold mb-2">Prova oro scuro · gemme rosse originali</p>
    <div className="flex flex-wrap justify-center gap-2">
     <button type="button" aria-pressed={!matched} onClick={()=>setMatched(false)} className={"border border-gold px-3 py-2 "+(!matched?"bg-gold text-obsidian":"")}>Originale · rev. 18</button>
     <button type="button" aria-pressed={matched} onClick={()=>setMatched(true)} className={"border border-gold px-3 py-2 "+(matched?"bg-gold text-obsidian":"")}>Oro del retro · prova</button>
    </div>
    {proof?.color&&matched&&<p className="mt-2 flex justify-center items-center gap-2 text-xs"><span aria-hidden="true" style={{display:"inline-block",width:18,height:18,borderRadius:3,background:proof.color}}/>Oro campionato dal fregio del retro</p>}
    <p className="mt-2 text-xs">Maschera dedicata al master Armatura: i sei riquadri in pergamena, i rubini e i medaglioni sono esclusi dalla tinta. Esportazioni originali, prova soltanto visiva.</p>
   </div>}
   <div className="grid grid-cols-2 gap-2 max-w-[690px] mx-auto">
    <div className="min-w-0"><p className="text-xs mb-2">{matched&&proof?.matched?"FRONTE · ORO SCURO":"FRONTE · ORIGINALE"}</p><div style={previewStyle}>{proof?<img src={matched&&proof.matched?proof.matched:proof.front} alt="Fronte della carta campione" className="block w-full h-full"/>:<p className="text-xs">Preparazione…</p>}</div></div>
    <div className="min-w-0"><p className="text-xs mb-2">RETRO</p><div style={previewStyle}>{proof?<img src={proof.back} alt="Retro realmente esportato" className="block w-full h-full"/>:<p className="text-xs">Preparazione…</p>}</div></div>
   </div>
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
