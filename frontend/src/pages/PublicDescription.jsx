import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { BookOpen, ScrollText } from "lucide-react";
import { API } from "@/lib/api";

// Only saved card information already available in the public sharing endpoint.
// Private references, source PDFs, audit metadata and revision histories stay private.
const DETAIL_KEYS = [
  "azioni","azioni_bonus","reazioni","azioni_leggendarie","azioni_mitiche","azioni_tana",
  "raggi_oculari","attacchi","attacchi_speciali","tratti","tratti_razza","capacita","capacità",
  "capacita_speciali","abilità_speciali","abilita_speciali","caratteristiche_speciali",
  "resistenze","immunita","immunità","vulnerabilita","sensi","linguaggi","abilità",
  "abilita","effetto","effetti","descrizione_completa","testo_completo","benefici",
  "proprieta","proprietà","prerequisiti","prerequisito","componenti","durata",
  "a_livelli_superiori","livelli_superiori","potenziamento","incremento_livello",
  "privilegi","competenze","attunement","sintonia",
];
const visible = (value) => {
  if (value === null || value === undefined || value === "") return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") return Object.keys(value).length > 0;
  return typeof value !== "boolean";
};
const fieldLabel = (value) => value.replace(/_/g, " ").replace(/^./, s=>s.toUpperCase());
const itemText = (entry) => {
  if (entry === null || entry === undefined) return "";
  if (typeof entry === "string" || typeof entry === "number") return String(entry);
  if (Array.isArray(entry)) return entry.map(itemText).filter(Boolean).join(" · ");
  if (typeof entry !== "object") return "";
  const title = entry.nome || entry.name || entry.titolo || "";
  const text = entry.descrizione || entry.description || entry.testo || entry.text ||
    entry.effetto || entry.danno || entry.attacco || "";
  return [title, text].filter(Boolean).map(itemText).join(" — ");
};
export const publicCardDetails = (card) => DETAIL_KEYS
  .filter(key => visible(card?.attributes?.[key]))
  .map(key => ({ key, title:fieldLabel(key), value:card.attributes[key] }))
  .filter(section => itemText(section.value));

export default function PublicDescription() {
  const { id } = useParams();
  const [card,setCard] = useState(null);
  const [error,setError] = useState(false);
  useEffect(()=>{
    let active=true;
    setError(false);setCard(null);
    fetch(`${API}/public/cards/${encodeURIComponent(id)}`)
      .then(r=>{if(!r.ok)throw Error("Carta non disponibile");return r.json();})
      .then(data=>{if(active)setCard(data);})
      .catch(()=>{if(active)setError(true);});
    return()=>{active=false;};
  },[id]);
  return <div className="min-h-screen bg-[#141016] text-[#f6e9cc]">
    <header className="border-b border-[#c69c53]/50 py-5 px-5">
      <Link to="/" className="flex items-center justify-center gap-3 text-[#f1c878] tracking-[.2em] font-label">
        <BookOpen size={22}/> TOMOFORGE
      </Link>
    </header>
    <main className="max-w-3xl mx-auto px-5 py-10">
      {error ? <section className="text-center space-y-3">
        <ScrollText className="mx-auto text-[#d5ad67]"/>
        <h1 className="font-heading text-3xl">Descrizione non disponibile</h1>
        <p className="text-[#e1caa8]">La carta non è stata trovata o non è più disponibile.</p>
      </section> : !card ? <p className="text-center text-[#dabb83]">Apertura della pergamena…</p> :
      <article className="rounded-xl border-2 border-[#c89e54] bg-[#f5e8c5] text-[#291a10] shadow-xl">
        <div className="bg-gradient-to-r from-[#a6783b] via-[#fff5d8] to-[#ab793b] p-7 border-b border-[#ad7b3b] text-center">
          <p className="text-xs tracking-widest uppercase font-label">Descrizione completa</p>
          <h1 className="font-heading text-4xl mt-2">{card.name}</h1>
        </div>
        <div className="p-6 sm:p-9 space-y-8">
          {card.description && <section>
            <h2 className="font-heading text-2xl mb-3">Descrizione</h2>
            <p className="font-body text-lg leading-relaxed whitespace-pre-wrap">{card.description}</p>
          </section>}
          {card.story && <section>
            <h2 className="font-heading text-2xl mb-3">Storia</h2>
            <p className="font-body text-lg leading-relaxed whitespace-pre-wrap">{card.story}</p>
          </section>}
          {publicCardDetails(card).map(section=><section key={section.key}
             className="border-t border-[#b89968] pt-5">
            <h2 className="font-heading text-2xl mb-3">{section.title}</h2>
            {Array.isArray(section.value) ? <div className="space-y-3">
              {section.value.map((entry,i)=><p key={i} className="font-body leading-relaxed whitespace-pre-wrap">{itemText(entry)}</p>)}
            </div> : <p className="font-body leading-relaxed whitespace-pre-wrap">{itemText(section.value)}</p>}
          </section>)}
        </div>
      </article>}
    </main>
  </div>;
}
