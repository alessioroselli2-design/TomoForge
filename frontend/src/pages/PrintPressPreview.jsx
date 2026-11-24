import React from "react";
import jsPDF from "jspdf";
import { CardFront, CardBack } from "@/components/TradingCard";
import { PRESS_SPEC, addPressCardPages } from "@/lib/pressExport";
import { addSingleCardA4PdfPages, createCardPng, createCardBackPng } from "@/lib/cardExport";

const SAMPLES=[
 {type:"monster",name:"Drago Rosso Adulto",attributes:{tipo_creatura:"Drago",taglia:"Enorme",allineamento:"Caotico Malvagio",grado_sfida:"17",classe_armatura:"19",punti_ferita:"256",velocita:"12 m",for:"27",des:"10",cos:"25",int:"16",sag:"13",car:"21"}},
 {type:"class",name:"Druido",attributes:{dado_vita:"d8",abilita_primaria:"Saggezza",tiri_salvezza:"Intelligenza, Saggezza",competenze:"Armature leggere, scudi"}},
 {type:"spell",name:"Palla di Fuoco",attributes:{livello:"3",scuola:"Invocazione",tempo_lancio:"1 azione",gittata:"45 m",danno:"8d6 fuoco"}},
 {type:"race",name:"Elfo",attributes:{taglia:"Media",velocita:"9 m"}},
 {type:"feature",name:"Forma Selvatica",attributes:{classe:"Druido",livello:"2"}},
 {type:"feat",name:"Maestro d'Armi",attributes:{bonus_caratteristica:"+1 Forza o Destrezza"}},
 {type:"item",name:"Bastone dei Boschi",attributes:{tipo:"Bastone",rarita:"Raro"}},
 {type:"weapon",name:"Spada Lunga",attributes:{danno:"1d8",tipo_danno:"Tagliente",proprieta:"Versatile (1d10)"}},
 {type:"armor",name:"Cotta di Maglia",attributes:{categoria_armatura:"pesante",classe_armatura:"16"}},
 {type:"character",name:"Personaggio · Luce",back:{variant:"luminous"},attributes:{classe:"Druido",livello:"5"}},
 {type:"character",name:"Personaggio · Argento",back:{variant:"silver"},attributes:{classe:"Druido",livello:"5"}},
];
export default function PrintPressPreview(){
 const [index,setIndex]=React.useState(0);
 const [busy,setBusy]=React.useState(false);
 const [feedback,setFeedback]=React.useState("");
 const ref=React.useRef(null);
 const card=React.useMemo(()=>({...SAMPLES[index],description:"Carta dimostrativa per il confronto del fronte e del retro. Nessun dato viene salvato."}),[index]);
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
   <p className="my-3 text-xs text-foreground/75">Anteprima PR #704 · revisione cornici 2 · renderer reale · nessun login, nessuna modifica alla collezione.</p>
   <label className="block my-4 text-sm">Scegli una carta
    <select disabled={busy} value={index} onChange={e=>{setIndex(Number(e.target.value));setFeedback("");}} className="block mx-auto mt-2 p-2 border border-gold-deep bg-card text-foreground">
     {SAMPLES.map((s,i)=><option key={i} value={i}>{s.name}</option>)}
    </select>
   </label>
   <div className="grid grid-cols-2 gap-2 max-w-[690px] mx-auto">
    <div className="min-w-0"><p className="text-xs mb-2">FRONTE</p><div style={{width:"100%",aspectRatio:"5/7"}}><CardFront card={card}/></div></div>
    <div className="min-w-0"><p className="text-xs mb-2">RETRO</p><div style={{width:"100%",aspectRatio:"5/7"}}><CardBack card={card}/></div></div>
   </div>
   <div className="flex flex-wrap justify-center gap-3 mt-6">
    <button disabled={busy} onClick={()=>download(true)} className="border border-gold bg-gold text-obsidian px-4 py-3 text-sm">SCARICA PDF TIPOGRAFIA</button>
    <button disabled={busy} onClick={()=>download(false)} className="border border-gold px-4 py-3 text-sm">SCARICA PDF A4</button>
    <button disabled={busy} onClick={()=>downloadPng(false)} className="border border-gold px-4 py-3 text-sm">PNG FRONTE</button>
    <button disabled={busy} onClick={()=>downloadPng(true)} className="border border-gold px-4 py-3 text-sm">PNG RETRO</button>
   </div>
   <p role="status" className="mt-3 text-sm">{feedback}</p>
   <p className="mt-3 text-xs text-foreground/70">PDF tipografia: taglio 63,5 × 88,9 mm, 3 mm abbondanza. PDF A4: stampa al 100%, fronte-retro sul lato lungo.</p>
   <div aria-hidden="true" style={{position:"fixed",left:-99999,top:0,width:340,height:476}} ref={ref}><CardFront card={card} exportMode/></div>
  </div>
 </main>;
}
