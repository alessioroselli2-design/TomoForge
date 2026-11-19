// Presentation-only model for the independent Incantesimo card.
// Never mutate imported records or infer a saving throw from a spell name.
const SCHOOLS = [
  'Abiurazione','Ammaliamento','Divinazione','Evocazione',
  'Illusione','Invocazione','Necromanzia','Trasmutazione',
];
export const SPELL_SCHOOLS = Object.freeze(SCHOOLS);
const slug = s => String(s ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g,'')
  .toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
const SCHOOL_ALIASES = {
  abjuration:'abiurazione', enchantment:'ammaliamento', divination:'divinazione',
  conjuration:'evocazione', illusion:'illusione', evocation:'invocazione',
  necromancy:'necromanzia', transmutation:'trasmutazione',
};
const simple = value => {
  if (value == null) return '';
  if (typeof value === 'string' || typeof value === 'number') return String(value).trim();
  if (Array.isArray(value)) return value.map(simple).filter(Boolean).join(', ');
  return '';
};
const pick = (attrs,keys) => keys.map(key=>simple(attrs[key])).find(Boolean)||'';
const flag = x => x === true || /^(?:true|1|si|sì|yes|rituale|concentrazione)$/i.test(simple(x));
const shrink = (text,limit=95) => {
  const s=String(text||'').replace(/\s+/g,' ').trim();
  return s.length<=limit?s:s.slice(0,limit-1).replace(/\s+\S*$/,'')+'…';
};
export const spellSchool = (raw) => {
  const key = SCHOOL_ALIASES[slug(raw)] || slug(raw);
  return SCHOOLS.find(s=>slug(s)===key) || '';
};
export const spellSchoolAsset = raw => {
  const index=SCHOOLS.indexOf(spellSchool(raw));
  return index<0?'':`/emblemi/scuole/scl-${String(index+1).padStart(2,'0')}-${slug(SCHOOLS[index])}.png`;
};
// Library records may contain a printed rule block before the actual effect.
// This parser changes only presentation: imported source remains unmodified.
export const splitSpellDescription = source => {
 const original=simple(source).replace(/\s+/g,' ').trim();
 const higher=/\b(?:Agli|Ai|Al|A)\s+Livelli\s+(?:Superiori|Pi[uù]\s+Alti)\s*[:.]\s*/i;
 const upcastAt=original.search(higher);
 const upcast=upcastAt<0?'':original.slice(upcastAt).replace(higher,'').trim();
 const unscaled=upcastAt<0?original:original.slice(0,upcastAt).trim();
 let narrative=unscaled;
 const fields={};
 const marker=/\b(Tempo\s+di\s+Lancio|Gittata|Componenti|Durata)\s*:\s*/gi;
 const marks=[...unscaled.matchAll(marker)];
 const pref=marks.length?unscaled.slice(0,marks[0].index).trim():'';
 if(marks.length>=2&&marks[0].index<100&&
   (!pref||/\b(?:livello|trucchetto|incantesimo)\b/i.test(pref))){
  for(let i=0;i<marks.length;i++){
   const mark=marks[i],key=mark[1].toLowerCase().replace(/\s+/g,' ');
   const start=mark.index+mark[0].length;
   const value=unscaled.slice(start,marks[i+1]?.index).trim();
   if(i<marks.length-1){fields[key]=value;continue;}
   const known=key==='durata'
    ? value.match(/^((?:concentrazione\s*,?\s*(?:fino a\s+)?|concentration\s*,?\s*(?:up to\s+)?)?(?:istantanea|instantaneous|permanente|(?:fino a\s+)?\d+\s*(?:rounds?|turni?|minut[oi]|minutes?|or[ae]|hours?|giorn[oi]|days?|settimane?|weeks?)))/i)
    : key==='componenti'
      ? value.match(/^([VSM](?:\s*,\s*[VSM]){0,2}(?:\s*\([^)]*\))?)/i)
      : null;
   if(known){fields[key]=known[1].trim();narrative=value.slice(known[1].length).trim();}
   else {narrative=unscaled;break;}
  }
 }
 // Narrative stays on the card, mechanics stay in the full source and stat grid.
 const phrases=narrative.split(/(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ])/);
 const visual=[];
 for(const phrase of phrases){
  if(visual.length && /\b(?:tiro\s+salvezza|tiri\s+salvezza|danni?\s+da|danni?\s+di|slot\s+incantesimo|livelli\s+superiori|ogni\s+creatura\s+deve)\b/i.test(phrase))break;
  visual.push(phrase);
 }
 return {narrative:visual.join(' ').trim(),fullEffect:narrative,fields,upcast};
};
const inferredSave = text => {
 const m=text.match(/\b(?:tiro|tiri)\s+(?:di\s+)?salvezza\s+(?:su|di|sulla|in)\s+(Forza|Destrezza|Costituzione|Intelligenza|Saggezza|Carisma)\b/i);
 return m?.[1]||'';
};
const inferredArea = text => {
 const m=text.match(/\b(sfera|cono|cubo|cilindro)\b.{0,65}?\b(raggio|lato|lunghezza|altezza)\s+(?:di\s+)?(\d+(?:[.,]\d+)?)\s*(?:metri|metro|m)\b/i);
 const fallback=m||text.match(/\b(sfera|cono|cubo|cilindro)\s+(?:di\s+)?(\d+(?:[.,]\d+)?)\s*(?:metri|metro|m)\s+di\s+(raggio|lato|lunghezza|altezza)\b/i);
 return fallback?fallback[1][0].toUpperCase()+fallback[1].slice(1).toLowerCase()+', '+(m?fallback[2]:fallback[3]).toLowerCase()+' '+(m?fallback[3]:fallback[2])+' m':'';
};
const inferredDamageType = text => {
 const m=text.match(/\bdanni?\s+(?:da|di)\s+(fuoco|freddo|acido|fulmine|tuono|veleno|forza|radiosi?|necrotici?|psichici?|perforanti|contundenti|taglienti)\b/i);
 return m?m[1][0].toUpperCase()+m[1].slice(1).toLowerCase():'';
};
const compactComponents = value => {
 const text=simple(value);
 const m=text.match(/^\s*([VSM](?:\s*,\s*[VSM]){0,2})(?:\s|,|\(|$)/i);
 return m?m[1].replace(/\s+/g,'').split('').filter(x=>/[VSM]/i.test(x)).join(', '):text;
};

const normalSave = value => {
  const s=slug(value);
  const match = s.match(/\b(forza|destrezza|costituzione|intelligenza|saggezza|carisma|strength|dexterity|constitution|intelligence|wisdom|charisma|for|des|cos|int|sag|car)\b/);
  const names={strength:'For',forza:'For',for:'For',dexterity:'Des',destrezza:'Des',des:'Des',constitution:'Cos',costituzione:'Cos',cos:'Cos',intelligence:'Int',intelligenza:'Int',int:'Int',wisdom:'Sag',saggezza:'Sag',sag:'Sag',charisma:'Car',carisma:'Car',car:'Car'};
  return match?names[match[1]]:simple(value);
};
const saveOutcome = (raw,desc) => {
  const s=slug(raw);
  if (/meta|dimezz|half/.test(s))return 'metà';
  if (/nega|annull|evita|nessun|no effect|negat/.test(s))return 'nega';
  if (s)return shrink(raw,28);
  // Infer only when the verified description explicitly states the outcome.
  if (/\b(?:la\s+)?metà(?=\s|[.,;]|$)/i.test(desc)&&/\b(?:tiro\s+(?:salvezza|riuscito|superato)|se\s+lo\s+supera|tiro\s+fallito)\b/i.test(desc))return 'metà';
  if (/\b(?:nessun effetto|non subisce|evita completamente)\b/i.test(desc)&&/tiro\s+salvezza/i.test(desc))return 'nega';
  return '';
};
// Personal casting values come only from an explicit character context or preview input,
 // never from a generic spell record; spell names do not imply a fixed save DC.
export const buildSpellCardView = (card={},spellcasting=null) => {
  const a=card.attributes||{};
  const school=spellSchool(pick(a,['scuola','school']));
  const level=pick(a,['livello','level','livello_incantesimo'])||'';
  const source=simple(card.description)||pick(a,['descrizione','description','effetto'])||'';
  const parsed=splitSpellDescription(source);
  const fullEffect=parsed.fullEffect||source;
  const duration=pick(a,['durata','duration'])||parsed.fields.durata||'—';
  const concentration=flag(a.concentrazione)||/concentrazion|concentration/i.test(duration)||/\brichiede\s+concentrazione\b/i.test(fullEffect);
  const ritual=flag(a.rituale)||flag(a.ritual);
  const durationClean=duration.replace(/^(?:concentrazione[,;:]?\s*(?:fino\s+a\s*)?|concentration[,;:]?\s*(?:up\s+to\s*)?)/i,'').trim();
  const shownDuration=(concentration?'Conc. ':'')+(durationClean||'—');
  const desc=parsed.narrative;
  const save=normalSave(pick(a,['tiro_salvezza','tipo_tiro_salvezza','caratteristica_tiro_salvezza','ts','saving_throw','salvezza'])||inferredSave(fullEffect));
  const outcome=saveOutcome(pick(a,['esito_tiro_salvezza','effetto_tiro_salvezza','esito_ts','effetto_ts','salvezza_riuscita','successo_ts','save_success']),fullEffect);
  const attack=pick(a,['tipo_attacco','attacco_incantesimo','attacco_magico','spell_attack','attacco']);
  const pb=spellcasting?.bonusCompetenza, ability=spellcasting?.modificatoreIncantatore;
  const hasCasting=Number.isInteger(Number(pb))&&Number.isInteger(Number(ability))
    &&pb!=null&&ability!=null&&Number(pb)>=1&&Number(pb)<=6
    &&Number(ability)>=-5&&Number(ability)<=10;
  const spellDC=hasCasting?8+Number(pb)+Number(ability):null;
  const attackBonus=hasCasting?Number(pb)+Number(ability):null;
  const attackText=attackBonus===null?'':` ${attackBonus>=0?'+':''}${attackBonus}`;
  const saveOrAttack=save?`TS ${save}${spellDC===null?'':' CD '+spellDC}${outcome?' · '+outcome:''}`
    :attack?`Att. ${shrink(attack,17)}${attackText}`:'—';
  const quickEffect=pick(a,['effetto_rapido','effetto_breve','sintesi_effetto','quick_effect']);
  const area=pick(a,['area_effetto','area','forma_area','area_di_effetto','bersagli','bersaglio','target'])||inferredArea(fullEffect)||'—';
  const dtype=pick(a,['tipo_danno','damage_type','tipo_di_danno','condizione','effetto_tipo'])||inferredDamageType(fullEffect)||'—';
  const damageSource=pick(a,['formula_danno','danno','danni','damage'])||fullEffect;
  const dice=(damageSource.match(/\b\d+d(?:4|6|8|10|12|20)(?:\s*[+-]\s*\d+)?\b/i)||[])[0]?.replace(/\s+/g,'')||'';
  const die= (dice.match(/d(?:4|6|8|10|12|20)/i)||[])[0]?.toLowerCase()||'';
  const dieAsset=die?`/card-art/spell-dice/${die}-${['d12','d20'].includes(die)?'clean-v32':'blank-v31'}.webp`:'';
  const upcast=pick(a,['aumento_livello','livelli_superiori','ai_livelli_superiori','a_livelli_superiori','potenziamento','livelli_piu_alti','higher_levels','scaling'])||parsed.upcast;
  const footTitle=upcast?'Aumento di livello':'';
  const footText=upcast;
  const basics=[
    {label:'Tempo',value:pick(a,['tempo_lancio','tempo_di_lancio','casting_time','azione'])||parsed.fields['tempo di lancio']||'—',icon:'tempo'},
    {label:'Gittata',value:pick(a,['gittata','range','raggio_azione'])||parsed.fields.gittata||'—',icon:'gittata'},
    {label:'Durata',value:shownDuration||'—',icon:'durata'},
    {label:'Componenti',value:compactComponents(pick(a,['componenti','components'])||parsed.fields.componenti)||'—',icon:'componenti'},
  ];
  const combat=[
    {label:'TS / Attacco',value:saveOrAttack,icon:'tiro'},
    {label:'Area / Bersaglio',value:shrink(area,37),icon:'area'},
    {label:'Danno / Effetto',value:shrink(dtype!=='—'?dtype:quickEffect||dice||'—',33),icon:'danno'},
  ];
  return {
    name:simple(card.name)||'Incantesimo',school,
    subtitle:school?`Incantesimo di ${school}`:'Incantesimo',
    level:level === '0'?'0':level,levelLabel:level==='0'?'TRUC.':'LIV.',
    schoolAsset:spellSchoolAsset(school),basics,combat,description:desc,fullDescription:source,quickEffect,
    concentration,ritual,spellDC,attackBonus,footTitle,footText,damageFormula:dice,dieAsset,
  };
};