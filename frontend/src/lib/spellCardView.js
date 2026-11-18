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
  return index<0?'':`/emblemi/scuole/scl-${String(index+1).padStart(2,'0')}-${slug(SCHOOLS[index])}.webp`;
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
  if (/\bmetà\s+(?:dei\s+)?danni\b/i.test(desc)&&/tiro\s+(?:salvezza|riuscito|superato)/i.test(desc))return 'metà';
  if (/\b(?:nessun effetto|non subisce|evita completamente)\b/i.test(desc)&&/tiro\s+salvezza/i.test(desc))return 'nega';
  return '';
};
export const buildSpellCardView = (card={}) => {
  const a=card.attributes||{};
  const school=spellSchool(pick(a,['scuola','school']));
  const level=pick(a,['livello','level','livello_incantesimo'])||'';
  const duration=pick(a,['durata','duration'])||'—';
  const concentration=flag(a.concentrazione)||/concentrazion|concentration/i.test(duration);
  const ritual=flag(a.rituale)||flag(a.ritual);
  const durationClean=duration.replace(/^(?:concentrazione[,;:]?\s*(?:fino\s+a\s*)?|concentration[,;:]?\s*(?:up\s+to\s*)?)/i,'').trim();
  const shownDuration=(concentration?'Conc. ':'')+(durationClean||'—');
  const desc=simple(card.description)||pick(a,['descrizione','description','effetto'])||'';
  const save=normalSave(pick(a,['tiro_salvezza','tipo_tiro_salvezza','caratteristica_tiro_salvezza','ts','saving_throw','salvezza']));
  const outcome=saveOutcome(pick(a,['esito_tiro_salvezza','effetto_tiro_salvezza','esito_ts','effetto_ts','salvezza_riuscita','successo_ts','save_success']),desc);
  const attack=pick(a,['tipo_attacco','attacco_incantesimo','attacco_magico','spell_attack','attacco']);
  const saveOrAttack=save?`TS ${save}${outcome?' · '+outcome:''}`:attack?`Att. ${shrink(attack,17)}`:'—';
  const area=pick(a,['area_effetto','area','forma_area','area_di_effetto','bersagli','bersaglio','target'])||'—';
  const dtype=pick(a,['tipo_danno','damage_type','tipo_di_danno','condizione','effetto_tipo'])||'—';
  const damageSource=pick(a,['formula_danno','danno','danni','damage'])||desc;
  const dice=(damageSource.match(/\b\d+d(?:4|6|8|10|12|20)(?:\s*[+-]\s*\d+)?\b/i)||[])[0]?.replace(/\s+/g,'')||'';
  const die= (dice.match(/d(?:4|6|8|10|12|20)/i)||[])[0]?.toLowerCase()||'';
  const dieAsset=die?`/card-art/spell-dice/${die}-${['d12','d20'].includes(die)?'clean-v32':'blank-v31'}.webp`:'';
  const upcast=pick(a,['aumento_livello','livelli_superiori','ai_livelli_superiori','a_livelli_superiori','potenziamento','livelli_piu_alti','higher_levels','scaling']);
  const materials=pick(a,['materiali_costosi','componenti_materiali','materiali_consumati']);
  const footTitle=upcast?'Aumento di livello':materials?'Componenti materiali':ritual?'Rituale':'';
  const footText=upcast||materials||(ritual?'Può essere lanciato come rituale.':'');
  const basics=[
    {label:'Tempo',value:pick(a,['tempo_lancio','tempo_di_lancio','casting_time','azione'])||'—',icon:'tempo'},
    {label:'Gittata',value:pick(a,['gittata','range','raggio_azione'])||'—',icon:'gittata'},
    {label:'Durata',value:shownDuration||'—',icon:'durata'},
    {label:'Componenti',value:pick(a,['componenti','components'])||'—',icon:'componenti'},
  ];
  const combat=[
    {label:'TS / Attacco',value:saveOrAttack,icon:'tiro'},
    {label:'Area / Bersaglio',value:shrink(area,37),icon:'area'},
    {label:'Danno / Effetto',value:shrink(dtype==='—'&&dice?dice:dtype,33),icon:'danno'},
  ];
  return {
    name:simple(card.name)||'Incantesimo',school,
    subtitle:school?`Incantesimo di ${school}`:'Incantesimo',
    level:level === '0'?'0':level,levelLabel:level==='0'?'TRUC.':'LIV.',
    schoolAsset:spellSchoolAsset(school),basics,combat,description:desc,
    concentration,ritual,footTitle,footText,damageFormula:dice,dieAsset,
  };
};