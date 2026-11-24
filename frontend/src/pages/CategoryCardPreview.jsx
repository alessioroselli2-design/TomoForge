import React from "react";
import { CardFront } from "@/components/TradingCard";

const FIXTURES=[
 {type:"feat",name:"Maestro D’Armi",attributes:{bonus_caratteristica:"+1 Forza o Destrezza"},description:"Test grafico della disposizione dei benefici. Una seconda frase completa verifica la leggibilità del testo."},
 {type:"item",name:"Bastone dei Boschi",attributes:{tipo:"Bastone",rarita:"Raro",sintonia:"richiede sintonia con un druido",cariche_massime:10,recupero_cariche:"1d6+4 all’alba"},description:"Esempio grafico delle proprietà di un bastone magico. Testo utilizzato esclusivamente per il collaudo."},
 {type:"weapon",name:"Spada Lunga",attributes:{categoria_arma:"guerra_mischia",danno:"1d8",tipo_danno:"Tagliente",proprieta:"Versatile (1d10)",costo:"15 mo",peso:"1,5 kg"}},
 {type:"armor",name:"Cotta di Maglia",attributes:{categoria_armatura:"pesante",classe_armatura:"16",forza_minima:13,svantaggio_furtivita:true,peso_kg:27.5,costo:"75 mo",tempo_indossare:"10 minuti",tempo_togliere:"5 minuti"}},
 {type:"armor",name:"Scudo",attributes:{categoria_armatura:"scudo",classe_armatura:"+2 alla CA",svantaggio_furtivita:false,peso_kg:3,costo:"10 mo",tempo_indossare:"1 azione",tempo_togliere:"1 azione"}},
];
const LONG="Questa frase completa serve a misurare l'adattamento del testo al riquadro. Una seconda frase permette di controllare l'allineamento. La descrizione non deve mai sovrapporsi ai bordi. ";
export default function CategoryCardPreview(){
 const [index,setIndex]=React.useState(0);
 const [long,setLong]=React.useState(false);
 const [empty,setEmpty]=React.useState(false);
 const sample=FIXTURES[index];
 const card=React.useMemo(()=>{
  if(empty)return {type:sample.type,name:sample.name,attributes:{}};
  if(!long)return sample;
  const attributes={...sample.attributes};
  if(sample.type==="feat"){attributes.benefici=LONG.repeat(5);attributes.prerequisito="Prerequisito dimostrativo particolarmente lungo";}
  if(sample.type==="item"){attributes.proprieta=LONG.repeat(5);attributes.sintonia="Sì · con un personaggio che soddisfa un requisito particolarmente lungo";}
  if(sample.type==="weapon"){attributes.proprieta=LONG.repeat(5);attributes.maestria="Proprietà dimostrativa";}
  if(sample.type==="armor"){attributes.dettagli=LONG.repeat(5);}
  return {...sample,name:sample.name+" — titolo dimostrativo esteso",attributes,description:LONG.repeat(5)};
 },[sample,long,empty]);
 return <main className="min-h-screen bg-obsidian text-gold px-3 py-6 sm:py-10" data-testid="category-card-preview">
 <div className="mx-auto max-w-2xl text-center">
 <h1 className="text-2xl font-display">TomoForge · Prova delle quattro categorie</h1>
 <p className="mt-2 mb-4 text-xs text-foreground/70">Renderer reale 5×7 · esempi grafici, non schede certificate · nessun login o salvataggio.</p>
 <nav className="flex gap-2 justify-center flex-wrap mb-4" aria-label="Carte da verificare">
 {FIXTURES.map((item,i)=><button key={item.name} type="button" onClick={()=>setIndex(i)} aria-pressed={i===index} className={"border border-gold-deep rounded px-2 py-2 text-xs "+(i===index?"bg-gold text-obsidian":"text-gold")}>{item.name}</button>)}
 </nav>
 <div className="flex gap-4 justify-center mb-4 text-xs flex-wrap">
 <label><input type="checkbox" checked={long} onChange={e=>setLong(e.target.checked)}/> Test testi lunghi</label>
 <label><input type="checkbox" checked={empty} onChange={e=>setEmpty(e.target.checked)}/> Test campi mancanti</label>
 </div>
 <div className="mx-auto" style={{width:"min(100%,340px)",aspectRatio:"5 / 7"}}><CardFront card={card}/></div>
 <p className="mt-4 text-xs text-foreground/60">PR #702 · collaudo grafico in sola lettura.</p>
 </div></main>;
}
