import {buildSpellCardView, SPELL_SCHOOLS, spellSchoolAsset} from './spellCardView';
import {readFileSync} from 'fs';
import {resolve} from 'path';

describe('new independent Incantesimo master — source-data presentation',()=>{
  it('maps the eight user-supplied school medals without an atlas, masks or invented glyphs',()=>{
    expect(SPELL_SCHOOLS).toHaveLength(8);
    SPELL_SCHOOLS.forEach((name,i)=>{
      const path=spellSchoolAsset(name);
      expect(path).toBe(`/emblemi/scuole/scl-${String(i+1).padStart(2,'0')}-${name.toLowerCase()}.webp`);
      const file=readFileSync(resolve(__dirname,`../../public${path}`));
      expect(file.subarray(0,4).toString()).toBe('RIFF');
      expect(file.subarray(8,12).toString()).toBe('WEBP');
    });
  });
  it('uses Invocazione for fireball, school-only subtitle, damage and a half-save',()=>{
    const view=buildSpellCardView({type:'spell',name:'Palla di Fuoco',attributes:{
      scuola:'Invocazione',livello:3,tempo_lancio:'1 azione',gittata:'45 m',durata:'Istantanea',
      componenti:'V, S, M',tiro_salvezza:'Destrezza',esito_ts:'metà',
      area_effetto:'Sfera, raggio 6 m',tipo_danno:'Fuoco',danno:'8d6',aumento_livello:'+1d6'}});
    expect(view.subtitle).toBe('Incantesimo di Invocazione');
    expect(view.schoolAsset).toContain('scl-06-invocazione.webp');
    expect(view.level).toBe('3');
    expect(view.basics.map(x=>x.value)).toEqual(['1 azione','45 m','Istantanea','V, S, M']);
    expect(view.combat[0].value).toBe('TS Des · metà');
    expect(view.damageFormula).toBe('8d6');
    expect(view.dieAsset).toBe('/card-art/spell-dice/d6-blank-v31.webp');
    expect(view.footTitle).toBe('Aumento di livello');
  });
  it('marks concentration while leaving non-damaging spells without a damage die',()=>{
    const view=buildSpellCardView({type:'spell',name:'Benedizione',attributes:{
      scuola:'Ammaliamento',livello:'1',concentrazione:true,durata:'1 minuto',bersagli:'3 creature'}});
    expect(view.basics[2].value).toBe('Conc. 1 minuto');
    expect(view.damageFormula).toBe('');
    expect(view.dieAsset).toBe('');
    expect(view.combat[0].value).toBe('—');
  });
  it('represents the explicit no-effect-on-success saving throw and cantrip level',()=>{
    const view=buildSpellCardView({type:'spell',name:'Prova',attributes:{
      scuola:'Enchantment',livello:'0',tiro_salvezza:'Saggezza',esito_ts:'nega'}});
    expect(view.school).toBe('Ammaliamento');
    expect(view.combat[0].value).toBe('TS Sag · nega');
    expect(view.levelLabel).toBe('TRUC.');
  });
  it('keeps every stat absent when missing instead of assigning fictitious rules',()=>{
    const v=buildSpellCardView({type:'spell',name:'Senza dati'});
    expect(v.basics.every(x=>x.value==='—')).toBe(true);
    expect(v.combat.every(x=>x.value==='—')).toBe(true);
    expect(v.footTitle).toBe('');
    expect(v.schoolAsset).toBe('');
  });
  it('retains the complete spell master without the Class fixed headings',()=>{
    const file=readFileSync(resolve(__dirname,'../../public/card-art/master-incantesimo-5x7-v1.webp'));
    expect(file.subarray(0,4).toString()).toBe('RIFF');
    expect(file.subarray(8,12).toString()).toBe('WEBP');
    expect(file.byteLength).toBeGreaterThan(100000);
  });
});
// New character-context rule: no generic spell ever invents a fixed CD.
describe('spell DC and quick effect without changes to approved Class renderer',()=>{
 it('never invents a default save DC for a generic spell',()=>{
   const v=buildSpellCardView({type:'spell',attributes:{tiro_salvezza:'Saggezza',esito_ts:'nega'}});
   expect(v.spellDC).toBeNull();
   expect(v.combat[0].value).toBe('TS Sag · nega');
 });
 it('calculates DC only when a character context is supplied',()=>{
   const card={type:'spell',attributes:{tiro_salvezza:'Saggezza',esito_ts:'nega',effetto_rapido:'Paralizzato se fallisce'}};
   const v=buildSpellCardView(card,{bonusCompetenza:3,modificatoreIncantatore:4});
   expect(v.spellDC).toBe(15);
   expect(v.combat[0].value).toBe('TS Sag CD 15 · nega');
   expect(v.quickEffect).toBe('Paralizzato se fallisce');
   expect(buildSpellCardView(card,{bonusCompetenza:4,modificatoreIncantatore:5}).spellDC).toBe(17);
 });
 it('preserves non-damaging quick effects without displaying damage dice',()=>{
   const v=buildSpellCardView({type:'spell',name:'Scudo',attributes:{effetto_rapido:'+5 CA fino al prossimo turno'}});
   expect(v.quickEffect).toContain('+5 CA');
   expect(v.dieAsset).toBe('');
   expect(v.damageFormula).toBe('');
 });
 it('keeps the approved Class emblem geometry while optically matching school artwork',()=>{
   const css=readFileSync(resolve(__dirname,'../components/SpellCardFront.css'),'utf8');
   expect(css).toContain('left:2.05%;top:.2786%;width:27.5%');
   expect(css).toContain('padding:2.15%;box-sizing:border-box');
   expect(css).toContain('left:74.6%;top:3.95%;width:19.2%;height:12.3%');
   expect(css).toContain('height:10.2%;grid-template-columns:repeat(4');
 });
});
