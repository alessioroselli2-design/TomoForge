import React from "react";
import {Hourglass,Target,Clock3,Shapes,ShieldCheck,Scan,Flame,Sparkles} from "lucide-react";
import {QRCodeCanvas} from "qrcode.react";
import {getFrontEmblem} from "@/lib/frontEmblems";
import {artworkUrl} from "@/lib/api";
import {publicDescriptionUrl} from "@/lib/cardDescription";
import "./SpellCardPreview.css";

const SCHOOL_NAMES=["Abiurazione","Ammaliamento","Divinazione","Evocazione","Illusione","Invocazione","Necromanzia","Trasmutazione"];
const nameKey=v=>String(v??"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().trim();
const ENGLISH_SCHOOL={abjuration:"Abiurazione",enchantment:"Ammaliamento",divination:"Divinazione",
  conjuration:"Evocazione",illusion:"Illusione",evocation:"Invocazione",necromancy:"Necromanzia",transmutation:"Trasmutazione"};
const readable=value=>typeof value==="string"||typeof value==="number"?String(value).trim():
  Array.isArray(value)?value.map(readable).filter(Boolean).join(", "):"";
const value=(attrs,names)=>names.map(n=>readable(attrs[n])).find(Boolean)||"";
const flag=v=>v===true||/^(true|1|si|sì|yes)$/i.test(readable(v));
const extractSave=v=>{
 const s=nameKey(v); const names={forza:"For",destrezza:"Des",costituzione:"Cos",intelligenza:"Int",
  saggezza:"Sag",carisma:"Car",for:"For",des:"Des",cos:"Cos",int:"Int",sag:"Sag",car:"Car",
  strength:"For",dexterity:"Des",constitution:"Cos",intelligence:"Int",wisdom:"Sag",charisma:"Car"};
 return Object.keys(names).map(n=>({n,idx:s.indexOf(n)})).filter(x=>x.idx>=0).sort((a,b)=>a.idx-b.idx)
   .map(x=>names[x.n])[0]||readable(v);
};
const truncate=(s,n=44)=>readable(s).length<=n?readable(s):readable(s).slice(0,n-1).trim()+"…";
export const spellPreviewData=(card={})=>{
 const a=card.attributes||{},originalSchool=value(a,["scuola","school"]);
 const school=SCHOOL_NAMES.find(n=>nameKey(n)===nameKey(originalSchool))||ENGLISH_SCHOOL[nameKey(originalSchool)]||originalSchool;
 const duration=value(a,["durata","duration"])||"—";
 const conc=flag(a.concentrazione)||/concentrazion|concentration/i.test(duration);
 const shortDuration=duration.replace(/^concentrazione[,;:]?\s*(?:fino\s+a\s*)?/i,"").trim();
 const save=value(a,["tiro_salvezza","tipo_tiro_salvezza","caratteristica_tiro_salvezza","ts","saving_throw","salvezza"]);
 const result=value(a,["esito_ts","effetto_ts","esito_tiro_salvezza","salvezza_riuscita","save_success"]);
 const outcome=/meta|dimezz|half/i.test(result)?"metà":/nega|annull|nessun|evita/i.test(result)?"nega":result;
 const attack=value(a,["tipo_attacco","attacco_magico","spell_attack"]);
 const saveText=save?"TS "+extractSave(save)+(outcome?" · "+outcome:""):attack?"Att. "+truncate(attack,20):"—";
 const dmg=value(a,["formula_danno","danno","danni","damage"])||"";
 const dice=(dmg.match(/\b\d+d(?:4|6|8|10|12|20)(?:\s*[+-]\s*\d+)?\b/i)||[])[0]?.replace(/\s+/g,"")||"";
 const die=(dice.match(/d(?:4|6|8|10|12|20)/i)||[])[0]?.toLowerCase()||"";
 const schoolIcon=getFrontEmblem({type:"spell",attributes:{scuola:school}});
 const lvl=value(a,["livello","level","livello_incantesimo"]);
 return {
   name:card.name||"Incantesimo",subtitle:school?"Incantesimo di "+school:"Incantesimo",level:lvl,school,schoolIcon,
   details:[
    {label:"Tempo",value:value(a,["tempo_lancio","tempo_di_lancio","casting_time","azione"])||"—",icon:Hourglass},
    {label:"Gittata",value:value(a,["gittata","range","raggio_azione"])||"—",icon:Target},
    {label:"Durata",value:(conc?"Conc. ":"")+(shortDuration||"—"),icon:Clock3},
    {label:"Componenti",value:value(a,["componenti","components"])||"—",icon:Shapes},
   ],
   tactics:[
    {label:"TS / Attacco",value:saveText,icon:ShieldCheck},
    {label:"Area / Bersaglio",value:truncate(value(a,["area_effetto","area","bersagli","bersaglio","target"])||"—",34),icon:Scan},
    {label:"Danno / Effetto",value:value(a,["tipo_danno","tipo_di_danno","damage_type","effetto_tipo"])|| (dice||"—"),icon:Flame}
   ],
   description:card.description||"La descrizione non è presente nel record.",
   dice,dieAsset:die?"/card-art/spell-dice/"+die+"-"+(["d12","d20"].includes(die)?"clean-v32":"blank-v31")+".webp":"",
   foot:value(a,["aumento_livello","livelli_superiori","ai_livelli_superiori","a_livelli_superiori","higher_levels","scaling"])||"",
   ritual:flag(a.rituale)||flag(a.ritual),
 };
};
const Stat=({entry,compact=false})=>{
 const Icon=entry.icon;
 return <div className={"tf-spell-stat "+(compact?"tf-spell-stat-small":"")} title={entry.label+": "+entry.value}>
   <Icon aria-hidden="true" className="tf-spell-stat-icon" strokeWidth={2.2}/>
   <div><b>{entry.label}</b><strong>{entry.value}</strong></div>
 </div>;
};
export const SpellCardPrototype=({card={},imgUrl="",editorMode=false})=>{
 const view=spellPreviewData(card);
 const icon=view.schoolIcon;
 const [bad,setBad]=React.useState(false);
 const src=imgUrl||(card.artwork_path?artworkUrl(card.artwork_path):"");
 const detailLink=publicDescriptionUrl(card);
 return <div className="tf-spell-prototype" data-testid="card-front" data-front-category="spell" data-front-layout="spell-prototype">
   <div className="tf-spell-covers" aria-hidden="true"/>
   {icon&&<div className="tf-spell-school" title={"Scuola di "+view.school} aria-label={"Scuola di "+view.school}>
      <div className="tf-spell-school-sprite" style={{backgroundImage:"url("+icon.src+")",
        backgroundPosition:icon.backgroundPosition,backgroundSize:icon.backgroundSize}}/>
   </div>}
   <header className="tf-spell-heading"><h3>{view.name}</h3><p>{view.subtitle}</p></header>
   {view.level!==""&&<div className="tf-spell-level" aria-label={"Livello "+view.level}>
     <strong>{view.level}</strong><span>{view.level==="0"?"TRUC.":"LIV."}</span>
   </div>}
   <section className="tf-spell-artwork">
     {src&&!bad?<img src={src} crossOrigin="anonymous" alt={view.name} onError={()=>setBad(true)}/>:editorMode?<span>Illustrazione da caricare</span>:null}
   </section>
   <section className="tf-spell-main-stats">{view.details.map(v=><Stat entry={v} key={v.label}/>)}</section>
   <section className="tf-spell-tactical-stats">{view.tactics.map(v=><Stat entry={v} key={v.label} compact/>)}</section>
   <section className={"tf-spell-description "+(view.dice?"tf-spell-with-die":"")}><p>{view.description}</p></section>
   {view.dieAsset&&<div className="tf-spell-die" aria-label={"Danni "+view.dice}>
      <img src={view.dieAsset} alt=""/><strong>{view.dice}</strong>
   </div>}
   {(view.foot||view.ritual)&&<section className="tf-spell-upcast">
      <b>{view.foot?"Aumento di livello":"Rituale"}</b>
      <p>{view.foot||(view.ritual?"Può essere lanciato come rituale.":"")}</p>
   </section>}
   {detailLink&&<a className="tf-spell-qr" data-card-qr href={detailLink} target="_blank"
      rel="noopener noreferrer" title="Descrizione completa"><QRCodeCanvas value={detailLink} size={46} level="M" marginSize={1}/></a>}
 </div>;
};
const DEMOS=[
 {name:"Palla di Fuoco",data:{type:"spell",name:"Palla di Fuoco",
   attributes:{scuola:"Invocazione",livello:"3",tempo_lancio:"1 azione",gittata:"45 m",
   durata:"Istantanea",componenti:"V, S, M",tiro_salvezza:"Destrezza",esito_ts:"metà",
   area_effetto:"Sfera, raggio 6 m",tipo_danno:"Fuoco",danno:"8d6",aumento_livello:"+1d6 per slot superiore al 3°"},
   description:"Una sfera di fuoco esplode in un punto a tua scelta. Ogni creatura nell'area effettua un tiro salvezza su Destrezza: subisce 8d6 danni da fuoco con un tiro fallito, o la metà con un tiro riuscito."}},
 {name:"Benedizione",data:{type:"spell",name:"Benedizione",
   attributes:{scuola:"Ammaliamento",livello:"1",tempo_lancio:"1 azione",gittata:"9 m",durata:"1 minuto",
   concentrazione:true,componenti:"V, S, M",bersagli:"Fino a 3 creature",effetto_tipo:"Beneficio"},
   description:"Fino a tre creature a tua scelta ricevono un beneficio ai tiri per colpire e ai tiri salvezza per la durata dell'incantesimo."}},
 {name:"Blocca Persone",data:{type:"spell",name:"Blocca Persone",
   attributes:{scuola:"Ammaliamento",livello:"2",tempo_lancio:"1 azione",gittata:"18 m",durata:"1 minuto",
   concentrazione:true,componenti:"V, S, M",bersaglio:"1 umanoide",tiro_salvezza:"Saggezza",
   esito_ts:"nega",effetto_tipo:"Paralizzato",aumento_livello:"+1 bersaglio per slot superiore al 2°"},
   description:"Un umanoide deve effettuare un tiro salvezza su Saggezza o rimane paralizzato. Può ripetere il tiro nei turni successivi."}},
 {name:"Scudo",data:{type:"spell",name:"Scudo",
   attributes:{scuola:"Abiurazione",livello:"1",tempo_lancio:"1 reazione",gittata:"Sé stesso",durata:"1 round",
   componenti:"V, S",bersaglio:"Sé stesso",effetto_tipo:"Difesa"},
   description:"Una barriera invisibile ti protegge fino all'inizio del tuo turno successivo, aumentando la Classe Armatura."}}
];
export default function SpellCardPreview(){
 const [choice,setChoice]=React.useState(0);const [schools,setSchools]=React.useState(false);
 return <main className="min-h-screen bg-obsidian text-gold px-3 py-8" data-testid="spell-preview">
 <div className="max-w-5xl mx-auto text-center">
  <h1 className="font-display text-2xl">TomoForge · Prova Incantesimi</h1>
  <p className="mt-2 mb-5 text-sm text-foreground/75">Bozza interattiva indipendente · esempi grafici, non record verificati · nessuna modifica alla produzione</p>
  <div className="flex gap-2 justify-center flex-wrap mb-6">{DEMOS.map((a,i)=><button key={a.name} type="button"
     onClick={()=>setChoice(i)} aria-pressed={choice===i}
     className={"border rounded px-3 py-2 "+(choice===i?"bg-gold text-obsidian border-gold":"border-gold-deep text-gold")}>{a.name}</button>)}</div>
  <div className="mx-auto" style={{width:"min(100%,360px)",aspectRatio:"5 / 7"}}>
    <SpellCardPrototype key={choice} card={DEMOS[choice].data} editorMode/>
  </div>
  <p className="mt-5 text-xs text-foreground/70">Simboli temporanei dal catalogo presente nell'app; gli 8 medaglioni della tavola allegata sono preparati per la sostituzione.</p>
  <button type="button" onClick={()=>setSchools(v=>!v)} className="mt-4 border border-gold-deep rounded px-3 py-2">
    {schools?"Nascondi scuole":"Mostra le otto scuole"}</button>
  {schools&&<div className="max-w-3xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
    {SCHOOL_NAMES.map(n=>{const s=getFrontEmblem({type:"spell",attributes:{scuola:n}});
      return <div key={n} className="border border-gold-deep/50 rounded p-2">
        <div className="tf-spell-school-preview" style={{backgroundImage:"url("+s.src+")",backgroundSize:s.backgroundSize,backgroundPosition:s.backgroundPosition}}/>
        <p className="text-xs mt-2">{n}</p>
      </div>})}
  </div>}
 </div></main>;
}