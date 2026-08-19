import React, { useEffect, useState, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Wand2, ImagePlus, Upload, Save, ArrowLeft, Loader2, Palette, PenLine, Crown } from "lucide-react";
import { api } from "@/lib/api";
import { CARD_TYPES, EMBLEMS, BACK_STYLES, DEFAULT_APPEARANCE, attrLabel } from "@/lib/cardTypes";
import Navbar from "@/components/Navbar";
import { PremiumDialog } from "@/components/PremiumDialog";
import { CardAppearanceControls } from "@/components/CardAppearanceControls";
import { useAuth } from "@/context/AuthContext";
import { CardFront, CardBack } from "@/components/TradingCard";
import AttributeEditor from "@/components/AttributeEditor";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const DEFAULT_ATTRS = {
  spell: { livello: "", scuola: "", azione: "", tempo_lancio: "", gittata: "", area: "", componenti: "", durata: "", concentrazione: "", danno: "", effetto: "" },
  class: { dado_vita: "", abilita_primaria: "", tiri_salvezza: "", competenze: "", caratteristiche: [] },
  race: { bonus_caratteristiche: "", velocita: "", taglia: "", linguaggi: "", tratti: [] },
  weapon: { danno: "", tipo_danno: "", proprieta: "", peso: "", costo: "", categoria: "" },
  feat: { prerequisito: "", benefici: [] },
  monster: { classe_armatura: "", punti_ferita: "", velocita: "", for: "", des: "", cos: "", int: "", sag: "", car: "", tiri_salvezza: "", resistenze: "", vulnerabilita: "", immunita: "", sensi: "", linguaggi: "", grado_sfida: "", azioni: [{ nome: "", descrizione: "" }] },
  character: { classe: "", razza: "", livello: "", for: "", des: "", cos: "", int: "", sag: "", car: "", bonus_competenza: "", classe_armatura: "", punti_ferita: "", cd_incantesimi: "", competenze: "", abilita_sottoclasse: [], slot_incantesimi: [] },
  custom: {},
};

const inputCls = "bg-input border-border rounded-none font-body focus-visible:ring-gold";

export default function CardEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isEdit = !!id;
  const fileRef = useRef(null);
  const [premiumOpen, setPremiumOpen] = useState(false);

  const [card, setCard] = useState({
    type: "spell", custom_type: "", name: "", description: "", story: "",
    language: "it", attributes: { ...DEFAULT_ATTRS.spell }, artwork_path: null,
    frame: "gold",
    appearance: { ...DEFAULT_APPEARANCE },
    back: { style: "classic", color: "#7f1d1d", emblem: "flame", motto: "" },
  });
  const [prompt, setPrompt] = useState("");
  const [genText, setGenText] = useState(false);
  const [genImg, setGenImg] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showBack, setShowBack] = useState(false);

  useEffect(() => {
    if (!isEdit) return;
    (async () => {
      try {
        const res = await api.get(`/cards/${id}`);
        setCard({
          ...res.data,
          appearance: { ...DEFAULT_APPEARANCE, ...(res.data.appearance || {}) },
          back: { style: "classic", color: "#7f1d1d", emblem: "flame", motto: "", ...(res.data.back || {}) },
        });
      } catch (e) {
        toast.error("Carta non trovata");
        navigate("/collezione");
      }
    })();
  }, [id, isEdit, navigate]);

  const set = (patch) => setCard((c) => ({ ...c, ...patch }));
  const setAppearance = (appearance) => setCard((c) => ({ ...c, appearance }));
  const setBack = (patch) => setCard((c) => ({ ...c, back: { ...c.back, ...patch } }));

  const onTypeChange = (type) => {
    set({ type, attributes: isEdit ? card.attributes : { ...DEFAULT_ATTRS[type] } });
  };

  const generateText = async () => {
    if (!user?.is_premium) { setPremiumOpen(true); return; }
    if (!prompt.trim()) { toast.error("Descrivi cosa vuoi evocare"); return; }
    setGenText(true);
    try {
      const res = await api.post("/ai/generate-content", {
        type: card.type, custom_type: card.custom_type, prompt, language: card.language,
      });
      set({
        name: res.data.name || card.name,
        description: res.data.description || card.description,
        story: res.data.story || card.story,
        attributes: res.data.attributes && Object.keys(res.data.attributes).length ? res.data.attributes : card.attributes,
      });
      toast.success("Contenuto evocato dall'arcano");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Generazione fallita");
    } finally {
      setGenText(false);
    }
  };

  const generateImage = async () => {
    if (!user?.is_premium) { setPremiumOpen(true); return; }
    const p = prompt.trim() || card.name.trim() || card.description.trim();
    if (!p) { toast.error("Aggiungi un nome o una descrizione prima"); return; }
    setGenImg(true);
    try {
      const res = await api.post("/ai/generate-image", { prompt: p, type: card.type });
      set({ artwork_path: res.data.artwork_path });
      toast.success("Artwork evocato");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Generazione immagine fallita");
    } finally {
      setGenImg(false);
    }
  };

  const composeFree = () => {
    const a = card.attributes || {};
    const hasName = card.name.trim() !== "";
    const hasAttr = Object.values(a).some((v) => {
      if (Array.isArray(v)) return v.some((x) => (x && typeof x === "object") ? Object.values(x).some((s) => String(s).trim() !== "") : String(x).trim() !== "");
      return String(v).trim() !== "" && String(v).trim() !== "-";
    });
    if (!hasName && !hasAttr) {
      toast.error("Compila prima nome e qualche statistica");
      return;
    }
    const g = (k) => {
      const v = a[k];
      return v !== undefined && v !== null && String(v).trim() !== "" && String(v).trim() !== "-" ? String(v).trim() : null;
    };
    const name = card.name.trim() || "Questa carta";
    const parts = [];
    const t = card.type;

    if (t === "spell") {
      let s = `${name} è una magia`;
      if (g("scuola")) s += ` di ${g("scuola").toLowerCase()}`;
      if (g("livello")) s += ` di livello ${g("livello")}`;
      s += ".";
      parts.push(s);
      const cast = [];
      if (g("azione")) cast.push(`si lancia come ${g("azione").toLowerCase()}`);
      if (g("tempo_lancio") && !g("azione")) cast.push(`tempo di lancio ${g("tempo_lancio")}`);
      if (g("gittata")) cast.push(`gittata ${g("gittata")}`);
      if (g("area")) cast.push(`area ${g("area")}`);
      if (g("durata")) cast.push(`durata ${g("durata")}`);
      if (cast.length) parts.push(`${cast.join(", ")}.`.replace(/^./, (c) => c.toUpperCase()));
      if (g("concentrazione") && /s[ìi]/i.test(g("concentrazione"))) parts.push("Richiede concentrazione.");
      if (g("danno")) parts.push(`Infligge ${g("danno")}.`);
      if (g("effetto")) parts.push(g("effetto"));
    } else if (t === "weapon") {
      let s = `${name} è un'arma`;
      if (g("categoria")) s += ` ${g("categoria").toLowerCase()}`;
      if (g("danno")) s += ` che infligge ${g("danno")}`;
      if (g("tipo_danno")) s += ` danni ${g("tipo_danno").toLowerCase()}`;
      s += ".";
      parts.push(s);
      if (g("proprieta")) parts.push(`Proprietà: ${g("proprieta")}.`);
      if (g("peso") || g("costo")) parts.push([g("peso") && `Peso ${g("peso")}`, g("costo") && `costo ${g("costo")}`].filter(Boolean).join(", ") + ".");
    } else if (t === "monster") {
      let s = `${name} è una temibile creatura`;
      if (g("grado_sfida")) s += ` di grado sfida ${g("grado_sfida")}`;
      s += ".";
      parts.push(s);
      const st = [];
      if (g("classe_armatura")) st.push(`CA ${g("classe_armatura")}`);
      if (g("punti_ferita")) st.push(`${g("punti_ferita")} punti ferita`);
      if (g("velocita")) st.push(`velocità ${g("velocita")}`);
      if (st.length) parts.push(`Possiede ${st.join(", ")}.`);
      const res = [g("resistenze") && `resistenze a ${g("resistenze")}`, g("immunita") && `immunità a ${g("immunita")}`, g("vulnerabilita") && `vulnerabilità a ${g("vulnerabilita")}`].filter(Boolean);
      if (res.length) parts.push(`Ha ${res.join(", ")}.`);
    } else if (t === "character") {
      let s = `${name}`;
      const bio = [g("razza"), g("classe") && `${g("classe")}`].filter(Boolean).join(" ");
      if (bio) s += `, ${bio.toLowerCase()}`;
      if (g("livello")) s += ` di livello ${g("livello")}`;
      s += ".";
      parts.push(s);
      const st = [];
      if (g("classe_armatura")) st.push(`CA ${g("classe_armatura")}`);
      if (g("punti_ferita")) st.push(`${g("punti_ferita")} PF`);
      if (st.length) parts.push(st.join(", ") + ".");
    } else if (t === "race") {
      let s = `I ${name}`;
      const st = [];
      if (g("taglia")) st.push(`taglia ${g("taglia").toLowerCase()}`);
      if (g("velocita")) st.push(`velocità ${g("velocita")}`);
      s += st.length ? ` hanno ${st.join(" e ")}.` : " sono un popolo dalle antiche origini.";
      parts.push(s);
      if (g("linguaggi")) parts.push(`Parlano: ${g("linguaggi")}.`);
    } else if (t === "class") {
      let s = `${name} è una classe`;
      if (g("abilita_primaria")) s += ` incentrata su ${g("abilita_primaria")}`;
      s += ".";
      parts.push(s);
      if (g("dado_vita")) parts.push(`Dado vita: ${g("dado_vita")}.`);
      if (g("tiri_salvezza")) parts.push(`Tiri salvezza: ${g("tiri_salvezza")}.`);
    } else if (t === "feat") {
      parts.push(`${name} è un talento che conferisce vantaggi unici.`);
      if (g("prerequisito")) parts.push(`Prerequisito: ${g("prerequisito")}.`);
    } else {
      parts.push(`${name}.`);
      const extra = Object.keys(a)
        .filter((k) => g(k))
        .slice(0, 6)
        .map((k) => `${attrLabel(k)}: ${g(k)}`);
      if (extra.length) parts.push(extra.join(" · ") + ".");
    }

    const description = parts.join(" ").replace(/\s+/g, " ").trim();
    if (!description || description === `${name}.`) {
      toast.error("Compila prima nome e qualche statistica");
      return;
    }
    const patch = { description };
    if (!card.story.trim()) {
      patch.story = `Le origini di ${name} si perdono tra le pagine ingiallite di antichi tomi, tramandate da generazioni di avventurieri.`;
    }
    set(patch);
    toast.success("Descrizione composta gratis (nessun credito usato)");
  };

  const onUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await api.post("/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      set({ artwork_path: res.data.artwork_path });
      toast.success("Immagine caricata");
    } catch (err) {
      toast.error("Caricamento fallito");
    } finally {
      setUploading(false);
    }
  };

  const save = async () => {
    if (!card.name.trim()) { toast.error("Dai un nome alla carta"); return; }
    setSaving(true);
    try {
      const payload = {
        type: card.type, custom_type: card.custom_type, name: card.name,
        description: card.description, story: card.story, language: card.language,
        attributes: card.attributes, artwork_path: card.artwork_path, frame: card.frame,
        appearance: card.appearance, back: card.back,
      };
      if (isEdit) {
        await api.put(`/cards/${id}`, payload);
        toast.success("Carta aggiornata");
        navigate(`/carta/${id}`);
      } else {
        const res = await api.post("/cards", payload);
        toast.success("Carta forgiata");
        navigate(`/carta/${res.data.id}`);
      }
    } catch (e) {
      toast.error("Salvataggio fallito");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-obsidian">
      <Navbar />
      <PremiumDialog open={premiumOpen} onOpenChange={setPremiumOpen} />
      <main className="max-w-7xl mx-auto px-4 sm:px-8 py-8">
        <button data-testid="back-btn" onClick={() => navigate(-1)} className="flex items-center gap-1.5 text-muted-foreground hover:text-gold font-label text-xs tracking-widest mb-6 transition-colors">
          <ArrowLeft className="w-4 h-4" /> INDIETRO
        </button>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-10">
          {/* FORM */}
          <div className="space-y-8">
            <div>
              <h1 className="font-display text-3xl sm:text-4xl tf-gold-text">{isEdit ? "Modifica Carta" : "Forgia una Carta"}</h1>
            </div>

            {/* Type + language */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label className="font-label text-xs tracking-widest text-gold/80">TIPO DI CARTA</Label>
                <Select value={card.type} onValueChange={onTypeChange}>
                  <SelectTrigger data-testid="type-select" className={`${inputCls} mt-2`}><SelectValue /></SelectTrigger>
                  <SelectContent className="bg-card border-gold-deep/40 rounded-none">
                    {CARD_TYPES.map((t) => (
                      <SelectItem key={t.id} value={t.id} className="font-body">{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="font-label text-xs tracking-widest text-gold/80">LINGUA CONTENUTO</Label>
                <div className="flex gap-2 mt-2">
                  {[["it", "Italiano"], ["en", "English"]].map(([code, lbl]) => (
                    <button key={code} data-testid={`lang-${code}`} onClick={() => set({ language: code })}
                      className={`flex-1 h-10 rounded-none border font-label text-xs tracking-wide transition-colors ${card.language === code ? "bg-gold text-obsidian border-gold" : "border-border text-muted-foreground hover:text-gold hover:border-gold-deep"}`}>
                      {lbl}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {card.type === "custom" && (
              <div>
                <Label className="font-label text-xs tracking-widest text-gold/80">NOME TIPO PERSONALIZZATO</Label>
                <Input data-testid="custom-type-input" value={card.custom_type || ""} onChange={(e) => set({ custom_type: e.target.value })}
                  placeholder="Es. Reliquia, Location, Fazione…" className={`${inputCls} mt-2`} />
              </div>
            )}

            {/* AI generation */}
            <div className="border border-gold-deep/40 bg-card p-5">
              <div className="flex items-center gap-2 mb-3">
                <Wand2 className="w-4 h-4 text-gold" />
                <span className="font-label text-xs tracking-widest text-gold">EVOCAZIONE ARCANA (AI)</span>
                {!user?.is_premium && (
                  <span className="flex items-center gap-1 border border-gold/50 px-1.5 py-0.5 font-label text-[9px] tracking-widest text-gold ml-auto">
                    <Crown className="w-3 h-3" /> PREMIUM
                  </span>
                )}
              </div>
              <Textarea data-testid="ai-prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)}
                placeholder="Descrivi la carta da evocare… es. 'Un antico drago di ghiaccio corrotto dal Piano Ombra'"
                className={`${inputCls} min-h-[70px]`} />
              <div className="flex flex-wrap gap-3 mt-3">
                <Button data-testid="gen-text-btn" onClick={generateText} disabled={genText}
                  className="rounded-none bg-gold text-obsidian hover:bg-gold-deep font-label text-xs tracking-wide animate-gold-pulse transition-colors">
                  {genText ? <Loader2 className="w-4 h-4 mr-1.5 animate-spin" /> : <Wand2 className="w-4 h-4 mr-1.5" />}
                  GENERA CONTENUTO
                </Button>
                <Button data-testid="gen-image-btn" onClick={generateImage} disabled={genImg} variant="outline"
                  className="rounded-none border-gold-deep/50 bg-transparent text-gold hover:bg-secondary font-label text-xs tracking-wide transition-colors">
                  {genImg ? <Loader2 className="w-4 h-4 mr-1.5 animate-spin" /> : <ImagePlus className="w-4 h-4 mr-1.5" />}
                  GENERA ARTWORK
                </Button>
                <Button data-testid="upload-btn" onClick={() => fileRef.current?.click()} disabled={uploading} variant="outline"
                  className="rounded-none border-border bg-transparent text-foreground hover:bg-secondary font-label text-xs tracking-wide transition-colors">
                  {uploading ? <Loader2 className="w-4 h-4 mr-1.5 animate-spin" /> : <Upload className="w-4 h-4 mr-1.5" />}
                  CARICA IMMAGINE
                </Button>
                <input ref={fileRef} type="file" accept="image/*" hidden onChange={onUpload} data-testid="file-input" />
              </div>
              <p className="font-body text-[11px] text-muted-foreground mt-2 italic">GENERA CONTENUTO e GENERA ARTWORK sono funzioni Premium e consumano crediti AI. Il caricamento immagine è gratuito.</p>
            </div>

            {/* Free (no-AI) composer */}
            <div className="border border-emerald-800/50 bg-emerald-950/10 p-5">
              <div className="flex items-center gap-2 mb-1">
                <PenLine className="w-4 h-4 text-emerald-400" />
                <span className="font-label text-xs tracking-widest text-emerald-300">COMPONI GRATIS (SENZA AI)</span>
              </div>
              <p className="font-body text-[12px] text-foreground/70 mb-3">
                Compila nome e statistiche qui sotto, poi crea automaticamente descrizione e storia dai campi inseriti. Nessun credito consumato.
              </p>
              <Button data-testid="compose-free-btn" onClick={composeFree}
                className="rounded-none bg-emerald-700 text-white hover:bg-emerald-600 font-label text-xs tracking-wide transition-colors">
                <PenLine className="w-4 h-4 mr-1.5" /> COMPONI DESCRIZIONE (GRATIS)
              </Button>
            </div>

            {/* Manual fields */}
            <div className="space-y-5">
              <div>
                <Label className="font-label text-xs tracking-widest text-gold/80">NOME</Label>
                <Input data-testid="name-field" value={card.name} onChange={(e) => set({ name: e.target.value })} className={`${inputCls} mt-2`} />
              </div>
              <div>
                <Label className="font-label text-xs tracking-widest text-gold/80">DESCRIZIONE</Label>
                <Textarea data-testid="desc-field" value={card.description} onChange={(e) => set({ description: e.target.value })} className={`${inputCls} mt-2 min-h-[80px]`} />
              </div>
              <div>
                <Label className="font-label text-xs tracking-widest text-gold/80">STORIA / LORE</Label>
                <Textarea data-testid="story-field" value={card.story} onChange={(e) => set({ story: e.target.value })} className={`${inputCls} mt-2 min-h-[80px]`} />
              </div>
            </div>

            {/* Attributes */}
            <div className="border-t border-border pt-6">
              <h2 className="font-heading text-2xl text-foreground mb-4">Statistiche & Attributi</h2>
              <AttributeEditor attributes={card.attributes} onChange={(a) => set({ attributes: a })} allowCustomFields={card.type === "custom"} />
            </div>

            <CardAppearanceControls
              frame={card.frame || "gold"}
              appearance={{ ...DEFAULT_APPEARANCE, ...(card.appearance || {}) }}
              onFrameChange={(frame) => set({ frame })}
              onAppearanceChange={setAppearance}
            />

            {/* Back customization */}
            <div className="border-t border-border pt-6">
              <div className="flex items-center gap-2 mb-4">
                <Palette className="w-5 h-5 text-gold" />
                <h2 className="font-heading text-2xl text-foreground">Retro della Carta</h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label className="font-label text-xs tracking-widest text-gold/80">STILE</Label>
                  <Select value={card.back.style} onValueChange={(v) => setBack({ style: v })}>
                    <SelectTrigger data-testid="back-style" className={`${inputCls} mt-2`}><SelectValue /></SelectTrigger>
                    <SelectContent className="bg-card border-gold-deep/40 rounded-none">
                      {BACK_STYLES.map((s) => <SelectItem key={s.id} value={s.id} className="font-body">{s.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="font-label text-xs tracking-widest text-gold/80">EMBLEMA</Label>
                  <Select value={card.back.emblem} onValueChange={(v) => setBack({ emblem: v })}>
                    <SelectTrigger data-testid="back-emblem" className={`${inputCls} mt-2`}><SelectValue /></SelectTrigger>
                    <SelectContent className="bg-card border-gold-deep/40 rounded-none">
                      {EMBLEMS.map((s) => <SelectItem key={s.id} value={s.id} className="font-body">{s.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="font-label text-xs tracking-widest text-gold/80">COLORE</Label>
                  <div className="flex items-center gap-3 mt-2">
                    <input type="color" data-testid="back-color" value={card.back.color} onChange={(e) => setBack({ color: e.target.value })}
                      className="w-12 h-10 bg-input border border-border cursor-pointer" />
                    <span className="font-body text-sm text-muted-foreground">{card.back.color}</span>
                  </div>
                </div>
                <div>
                  <Label className="font-label text-xs tracking-widest text-gold/80">MOTTO</Label>
                  <Input data-testid="back-motto" value={card.back.motto} onChange={(e) => setBack({ motto: e.target.value })}
                    placeholder="Es. Dalle ceneri, potere" className={`${inputCls} mt-2`} />
                </div>
              </div>
            </div>

            <Button data-testid="save-btn" onClick={save} disabled={saving}
              className="w-full sm:w-auto rounded-none bg-gold text-obsidian hover:bg-gold-deep font-label tracking-widest h-12 px-10 transition-colors">
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
              {isEdit ? "SALVA MODIFICHE" : "FORGIA LA CARTA"}
            </Button>
          </div>

          {/* PREVIEW */}
          <div className="lg:sticky lg:top-24 h-fit">
            <p className="font-label text-xs tracking-widest text-gold/70 mb-3 text-center">ANTEPRIMA</p>
            <motion.div layout className="mx-auto" style={{ width: 280, aspectRatio: "2.5/3.5" }}>
              {showBack ? <CardBack card={card} /> : <CardFront card={card} />}
            </motion.div>
            <div className="flex justify-center mt-4">
              <button data-testid="preview-flip" onClick={() => setShowBack((s) => !s)}
                className="font-label text-[11px] tracking-widest text-gold hover:text-gold-deep border border-gold-deep/50 px-4 py-2 transition-colors">
                {showBack ? "MOSTRA FRONTE" : "MOSTRA RETRO"}
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
