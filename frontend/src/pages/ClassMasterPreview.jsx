import React from "react";
import { CardFront } from "@/components/TradingCard";

const DATA = [
 ["Barbaro","d12","Forza","Forza, Costituzione","Armature leggere e medie, scudi, armi semplici e da guerra"],
 ["Bardo","d8","Carisma","Destrezza, Carisma","Armature leggere, armi semplici, balestre a mano, spade lunghe, stocchi, spade corte, tre strumenti musicali"],
 ["Chierico","d8","Saggezza","Saggezza, Carisma","Armature leggere e medie, scudi, armi semplici"],
 ["Druido","d8","Saggezza","Intelligenza, Saggezza","Armature leggere e medie, scudi, bastoni ferrati, pugnali, dardi, giavellotti, mazze, scimitarre, falcetti, fionde, lance, kit da erborista"],
 ["Guerriero","d10","Forza o Destrezza","Forza, Costituzione","Tutte le armature, scudi, armi semplici e da guerra"],
 ["Monaco","d8","Destrezza, Saggezza","Forza, Destrezza","Armi semplici, spade corte, uno strumento da artigiano o musicale"],
 ["Paladino","d10","Forza, Carisma","Saggezza, Carisma","Tutte le armature, scudi, armi semplici e da guerra"],
 ["Ranger","d10","Destrezza, Saggezza","Forza, Destrezza","Armature leggere e medie, scudi, armi semplici e da guerra"],
 ["Ladro","d8","Destrezza","Destrezza, Intelligenza","Armature leggere, armi semplici, balestre a mano, spade lunghe, stocchi, spade corte, arnesi da scasso"],
 ["Stregone","d6","Carisma","Costituzione, Carisma","Pugnali, dardi, fionde, bastoni ferrati, balestre leggere"],
 ["Warlock","d8","Carisma","Saggezza, Carisma","Armature leggere, armi semplici"],
 ["Mago","d6","Intelligenza","Intelligenza, Saggezza","Pugnali, dardi, fionde, bastoni ferrati, balestre leggere"],
 ["Artefice","d8","Intelligenza","Costituzione, Intelligenza","Armature leggere e medie, scudi, armi semplici, arnesi da scasso, strumenti da artigiano"]
];
const DESCRIPTION = "Questa classe sviluppa le proprie capacità attraverso l'esperienza e l'addestramento. I suoi privilegi cambiano nel corso dell'avventura e permettono di affrontare sfide differenti. Le competenze e le caratteristiche principali definiscono il modo in cui agisce, combatte e collabora con il gruppo. Questa frase aggiuntiva permette di verificare che la descrizione rimanga all'interno del riquadro senza tagliare parole o frasi.";
export default function ClassMasterPreview(){
 const [selected,setSelected]=React.useState(3);
 const cards=React.useMemo(()=>DATA.map(([name,die,primary,saves,proficiencies],index)=>({
  id:`demo-class-${index+1}`,type:"class",name,
  description:DESCRIPTION,
  attributes:{dado_vita:die,abilita_primaria:primary,tiri_salvezza:saves,competenze:proficiencies}
 })),[]);
 const [all,setAll]=React.useState(false);
 return <main data-testid="class-master-preview" className="min-h-screen bg-obsidian text-gold px-3 py-8">
  <header className="text-center max-w-2xl mx-auto">
   <p className="font-label text-xs tracking-widest">TOMO FORGE · COLLAUDO CLASSE 5×7</p>
   <h1 className="font-display text-2xl mt-3">Anteprima delle 13 carte Classe</h1>
   <p className="font-body text-sm mt-3 text-foreground/75">Questa pagina usa il renderer reale di TomoForge, senza accesso e senza modificare i dati. I testi sono dimostrativi: controlla master, emblema, dado, tre riquadri e descrizione.</p>
  </header>
  <div className="flex flex-wrap gap-2 justify-center my-6">
   {DATA.map(([name],index)=><button type="button" key={name} onClick={()=>{setSelected(index);setAll(false);}} className={`px-3 py-2 border rounded ${!all&&selected===index?"bg-gold text-obsidian":"border-gold text-gold"}`}>{name}</button>)}
   <button type="button" onClick={()=>setAll(v=>!v)} className="px-3 py-2 border border-gold rounded">{all?"Mostra una carta":"Mostra tutte e 13"}</button>
  </div>
  <div className={all?"flex flex-wrap justify-center gap-8":"flex justify-center"}>
   {(all?cards:[cards[selected]]).map(card=><section key={card.name} className="text-center" style={{width:all?280:340,maxWidth:"100%"}}>
    <div style={{width:"100%",aspectRatio:"340 / 476"}}><CardFront card={card} editorMode /></div>
    <p className="font-label text-sm mt-2">{card.name}</p>
   </section>)}
  </div>
  <p className="text-center font-body text-xs text-foreground/60 mt-8">Solo preview · nessun merge in produzione · nessuna modifica a Supabase</p>
 </main>;
}
