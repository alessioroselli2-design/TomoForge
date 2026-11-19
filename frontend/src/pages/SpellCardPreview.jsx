import React from 'react';
import {SpellCardFront} from '@/components/SpellCardFront';
import {SPELL_SCHOOLS,spellSchoolAsset} from '@/lib/spellCardView';

const PREVIEW=[
 {name:'Palla di Fuoco',image:'/card-art/spell-preview/palla-di-fuoco.webp',
  card:{type:'spell',name:'Palla di Fuoco',description:'Una brillante esplosione di fuoco investe ogni creatura nella sfera. Ogni bersaglio effettua un tiro salvezza su Destrezza: 8d6 danni da fuoco con un tiro fallito, o la metà con un tiro riuscito.',attributes:{scuola:'Invocazione',livello:'3',tempo_lancio:'1 azione',gittata:'45 m',durata:'Istantanea',componenti:'V, S, M',tiro_salvezza:'Destrezza',esito_ts:'metà',area_effetto:'Sfera, raggio 6 m',tipo_danno:'Fuoco',danno:'8d6',aumento_livello:'+1d6 danni per ogni slot superiore al 3°'}}},
 {name:'Benedizione',image:'',card:{type:'spell',name:'Benedizione',description:'Fino a tre creature a tua scelta aggiungono 1d4 ai tiri per colpire e ai tiri salvezza per la durata dell’incantesimo. Richiede concentrazione.',attributes:{scuola:'Ammaliamento',livello:'1',tempo_lancio:'1 azione',gittata:'9 m',durata:'1 minuto',concentrazione:true,componenti:'V, S, M',bersagli:'Fino a 3 creature',effetto_tipo:'Beneficio',effetto_rapido:'+1d4 a tiri per colpire e TS'}}},
 {name:'Blocca Persone',image:'',card:{type:'spell',name:'Blocca Persone',description:'Un umanoide effettua un TS Saggezza: se fallisce è paralizzato. Ripete il TS alla fine di ciascuno dei suoi turni per terminare l’effetto.',attributes:{scuola:'Ammaliamento',livello:'2',tempo_lancio:'1 azione',gittata:'18 m',durata:'1 minuto',concentrazione:true,componenti:'V, S, M',tiro_salvezza:'Saggezza',esito_ts:'nega',bersagli:'1 umanoide',effetto_tipo:'Paralizzato',effetto_rapido:'TS Sag nega · Paralizzato se fallisce · Ripete TS a fine turno',livelli_superiori:'+1 bersaglio per ogni livello di slot superiore al 2°'}}},
 {name:'Scudo',image:'',card:{type:'spell',name:'Scudo',description:'Fino all’inizio del tuo turno successivo hai +5 alla Classe Armatura, anche contro l’attacco che ha attivato la reazione, e non subisci danni da Dardo Incantato.',attributes:{scuola:'Abiurazione',livello:'1',tempo_lancio:'1 reazione',gittata:'Sé stesso',durata:'1 round',componenti:'V, S',bersaglio:'Sé stesso',effetto_tipo:'Difesa',effetto_rapido:'+5 CA fino al prossimo turno · Nessun danno da Dardo Incantato'}}},
];
export default function SpellCardPreview(){
 const [index,setIndex]=React.useState(0);
 const [showCatalog,setShowCatalog]=React.useState(false);
 const [bonusCompetenza,setBonusCompetenza]=React.useState(3);
 const [modificatoreIncantatore,setModificatoreIncantatore]=React.useState(4);
 const {name,card,image}=PREVIEW[index];
 return <main className="min-h-screen bg-obsidian text-gold px-3 py-8" data-testid="spell-preview">
  <div className="max-w-5xl mx-auto text-center">
   <h1 className="text-2xl font-display">TomoForge · Prova Incantesimi</h1>
   <p className="text-sm text-foreground/75 mt-2 mb-5">Renderer reale · esempi grafici dichiarati, nessuna modifica ai record o alle carte Classe/Mostro</p>
   <div className="flex gap-2 flex-wrap justify-center mb-5">
    {PREVIEW.map((item,i)=><button key={item.name} type="button" aria-pressed={i===index}
     className={`border rounded px-3 py-2 ${i===index?'bg-gold text-obsidian border-gold':'border-gold-deep text-gold'}`}
     onClick={()=>setIndex(i)}>{item.name}</button>)}
   </div>
   <div className="flex flex-wrap items-center justify-center gap-3 mb-5 text-sm text-foreground/90">
     <span>CD di prova = 8 + competenza + modificatore</span>
     <label>Competenza&nbsp;
       <select aria-label="Bonus competenza" className="bg-obsidian border border-gold-deep rounded px-2 py-1"
         value={bonusCompetenza} onChange={e=>setBonusCompetenza(Number(e.target.value))}>
         {[2,3,4,5,6].map(n=><option key={n} value={n}>+{n}</option>)}
       </select>
     </label>
     <label>Mod. incantatore&nbsp;
       <select aria-label="Modificatore da incantatore" className="bg-obsidian border border-gold-deep rounded px-2 py-1"
         value={modificatoreIncantatore} onChange={e=>setModificatoreIncantatore(Number(e.target.value))}>
         {[0,1,2,3,4,5,6].map(n=><option key={n} value={n}>{n>=0?'+':''}{n}</option>)}
       </select>
     </label>
     <strong>CD {8+bonusCompetenza+modificatoreIncantatore}</strong>
   </div>
   <div className="mx-auto" style={{width:'min(100%,360px)',aspectRatio:'5 / 7'}}>
    <SpellCardFront key={name} card={card} imgUrl={image||undefined} editorMode
      spellcasting={{bonusCompetenza,modificatoreIncantatore}} />
   </div>
   <p className="text-xs text-foreground/70 mt-5">{name} · carta dinamica di prova · i valori sono esempi per il collaudo, non record della biblioteca; la CD è solo simulata e non appartiene all'incantesimo</p>
   <button className="mt-4 border rounded border-gold-deep px-3 py-2 text-sm" type="button" onClick={()=>setShowCatalog(v=>!v)}>
    {showCatalog?'Nascondi scuole':'Mostra i simboli delle 8 scuole'}
   </button>
   {showCatalog&&<div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-3xl mx-auto">
     {SPELL_SCHOOLS.map(s=><div key={s} className="rounded border border-gold-deep/40 p-2">
      <img src={spellSchoolAsset(s)} alt={s} className="mx-auto h-28 w-28 object-contain"/>
      <div className="text-xs mt-2">{s}</div>
     </div>)}
   </div>}
  </div>
 </main>;
}