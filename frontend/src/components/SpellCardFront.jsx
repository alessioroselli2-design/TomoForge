import React from 'react';
import {QRCodeCanvas} from 'qrcode.react';
import {Hourglass, Crosshair, Clock3, Shapes, ShieldCheck, Scan, Sparkles} from 'lucide-react';
import {buildSpellCardView} from '@/lib/spellCardView';
const SPELL_PREVIEW_MASTER = '/card-art/front-restored-v18/master-incantesimo-5x7-v1.webp';
import {publicDescriptionUrl} from '@/lib/cardDescription';
import {artworkUrl} from '@/lib/api';
import './SpellCardFront.css';

const ICONS={tempo:Hourglass,gittata:Crosshair,durata:Clock3,componenti:Shapes,
  tiro:ShieldCheck,area:Scan,danno:Sparkles};
const Info = ({item,kind}) => {
  const Icon=ICONS[item.icon]||Sparkles;
  return <div className={`tf-spell-cell tf-spell-cell-${kind}`} title={`${item.label}: ${item.value}`}>
    <Icon className="tf-spell-field-icon" size={16} strokeWidth={2.3} aria-hidden="true"/>
    <div className="tf-spell-cell-copy"><span>{item.label}</span><strong>{item.value}</strong></div>
  </div>;
};

export const SpellCardFront=React.forwardRef(({card={},imgUrl,editorMode,exportMode,spellcasting},ref)=>{
  const v=buildSpellCardView(card,spellcasting);
  const [imageError,setImageError]=React.useState(false);
  const hasArtwork=Boolean(imgUrl||card.artwork_path);
  const src=imgUrl||(card.artwork_path?artworkUrl(card.artwork_path):'');
  React.useEffect(()=>setImageError(false),[src]);
  const detailsLink=publicDescriptionUrl(card);
  return <div ref={ref} data-testid="card-front" data-front-version="7"
    data-front-category="spell" data-front-layout="spell-5x7-v1" data-category-layout="spell-5x7-v1"
    className={`tf-spell-master ${exportMode?'tf-export-card':''}`}
    style={{backgroundImage:`url("${SPELL_PREVIEW_MASTER}")`}}>
    {v.schoolAsset&&<div className="tf-spell-school-medallion" data-testid="front-emblem" data-emblem-sprite="school-original">
      <img className="tf-spell-school-emblem" src={v.schoolAsset}
        alt={`Scuola di ${v.school}`} draggable={false}/>
    </div>}
    <header className="tf-spell-header">
      <h3 title={v.name}>{v.name}</h3><p>{v.subtitle}</p>
    </header>
    {v.level!==''&&<div className="tf-spell-level" aria-label={`Livello incantesimo ${v.level}`}>
      <strong>{v.level}</strong><span>{v.levelLabel}</span>
    </div>}
    <section className="tf-spell-picture" aria-label="Illustrazione dell'incantesimo">
      {hasArtwork&&!imageError&&<img src={src} alt={v.name} crossOrigin="anonymous"
        data-artwork-src={src} onError={()=>setImageError(true)} draggable={false}/>}
      {editorMode&&!hasArtwork&&<span className="tf-spell-art-hint">Illustrazione da caricare</span>}
    </section>
    <section className="tf-spell-basic-grid" data-testid="front-highlights" aria-label="Dati essenziali">
      {v.basics.map(item=><Info item={item} kind="basic" key={item.label}/>)}
    </section>
    <section className="tf-spell-combat-grid" aria-label="Dati tattici">
      {v.combat.map(item=><Info item={item} kind="combat" key={item.label}/>)}
    </section>
    <section className={`tf-spell-description ${v.damageFormula?'tf-spell-description-with-die':''}`}>
      <p>{v.description||'La descrizione dell’incantesimo non è presente nel record.'}</p>
    </section>
    {v.dieAsset&&<div className="tf-spell-damage" data-die={v.damageFormula}
       aria-label={`Danno ${v.damageFormula}`}>
       <img src={v.dieAsset} alt="" draggable={false}/><strong>{v.damageFormula}</strong>
    </div>}
    {v.footTitle&&<section className="tf-spell-footnote" data-testid="spell-upcast"
      title={v.footTextFull} aria-label={`${v.footTitle}: ${v.footTextFull}`}>
      <strong>{v.footTitle}</strong><p>{v.footText}</p>
    </section>}
    {detailsLink&&<a className="tf-spell-qr" data-card-qr href={detailsLink}
      target="_blank" rel="noopener noreferrer" title="Apri descrizione completa">
      <QRCodeCanvas value={detailsLink} size={46} level="M" marginSize={1}
        bgColor="#ffffff" fgColor="#10131c"/>
    </a>}
  </div>;
});
SpellCardFront.displayName='SpellCardFront';