import React, { useCallback, useEffect, useState, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Wand2, ImagePlus, Upload, Save, ArrowLeft, Loader2, Palette, PenLine, Crown, BookOpen, Search } from "lucide-react";
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
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Switch } from "@/components/ui/switch";

const DEFAULT_ATTRS = {
  spell: { livello: "", scuola: "", azione: "", tempo_lancio: "", gittata: "", area: "", componenti: "", durata: "", concentrazione: "", danno: "", effetto: "" },
  class: { dado_vita: "", abilita_primaria: "", tiri_salvezza: "", competenze: "", caratteristiche: [] },
  race: { bonus_caratteristiche: "", velocita: "", taglia: "", linguaggi: "", tratti: [] },
  weapon: { danno: "", tipo_danno: "", proprieta: "", gittata: "", peso: "", costo: "", categoria: "" },
  armor: { classe_armatura: "", forza_minima: "", svantaggio_furtivita: "", peso: "", costo: "", categoria: "" },
  item: { categoria: "", costo: "", peso: "", proprieta: "", rarita: "", sintonia: "" },
  feat: { prerequisito: "", benefici: [] },
  monster: { classe_armatura: "", punti_ferita: "", velocita: "", for: "", des: "", cos: "", int: "", sag: "", car: "", tiri_salvezza: "", resistenze: "", vulnerabilita: "", immunita: "", sensi: "", linguaggi: "", grado_sfida: "", azioni: [{ nome: "", descrizione: "" }] },
  character: { classe: "", razza: "", livello: "", for: "", des: "", cos: "", int: "", sag: "", car: "", bonus_competenza: "", classe_armatura: "", punti_ferita: "", cd_incantesimi: "", competenze: "", abilita_sottoclasse: [], slot_incantesimi: [] },
  custom: {},
};

const inputCls = "bg-input border-border rounded-none font-body focus-visible:ring-gold";
const LIBRARY_TYPES_BY_CARD = {
  spell: "spell",
  class: "class,subclass,class_feature",
  race: "race,subrace",
  feat: "feat",
  monster: "monster",
  weapon: "weapon",
  armor: "armor,shield",
  item: "equipment,tool,magic_item,vehicle,ammunition,mount,trade_good,service,other",
  custom: "ability,other",
};
const LIBRARY_TYPE_LABELS = {
  class: "Classe", subclass: "Sottoclasse", class_feature: "Privilegio di classe",
  spell: "Incantesimo",
  feat: "Talento", race: "Razza", subrace: "Sottorazza", monster: "Mostro",
  ability: "Capacità", weapon: "Arma", armor: "Armatura", shield: "Scudo",
  equipment: "Equipaggiamento", tool: "Strumento", magic_item: "Oggetto magico",
  vehicle: "Veicolo", ammunition: "Munizioni", mount: "Cavalcatura",
  trade_good: "Merce commerciale", service: "Servizio", other: "Contenuto del manuale",
};

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
  const [cleanupArtwork, setCleanupArtwork] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showBack, setShowBack] = useState(false);
  const [spellQuery, setSpellQuery] = useState("");
  const [spellResults, setSpellResults] = useState([]);
  const [searchingSpells, setSearchingSpells] = useState(false);
  const [applyingSpell, setApplyingSpell] = useState(null);
  const [referenceQuery, setReferenceQuery] = useState("");
  const [referenceResults, setReferenceResults] = useState([]);
  const [searchingReferences, setSearchingReferences] = useState(false);
  const [applyingReference, setApplyingReference] = useState(null);
  const [libraryManuals, setLibraryManuals] = useState([]);
  const [loadingManuals, setLoadingManuals] = useState(false);
  const [manualImporting, setManualImporting] = useState(false);
  const [retryingTranslation, setRetryingTranslation] = useState(null);
  const [selectedManual, setSelectedManual] = useState("");
  const [manualStartPage, setManualStartPage] = useState("5");
  const [manualEndPage, setManualEndPage] = useState("16");
  const [useManualOcr, setUseManualOcr] = useState(false);
  const [ocrConfirmed, setOcrConfirmed] = useState(false);
  const [translationConfirmed, setTranslationConfirmed] = useState(false);
  const [sourceRecord, setSourceRecord] = useState(null);
  const [loadingSourceRecord, setLoadingSourceRecord] = useState(null);
  const selectedManualInfo = libraryManuals.find((manual) => manual.filename === selectedManual);
  const selectedSpanishManual = selectedManualInfo?.source_language === "es";
  const useSelectedManualOcr = useManualOcr && selectedManualInfo?.source_language !== "es";

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
      toast.success(
        res.data.source === "grimorio" ? "Dati applicati dal Grimorio privato"
          : res.data.source === "biblioteca_privata" ? "Dati applicati dalla biblioteca privata"
            : "Contenuto evocato dall'arcano"
      );
    } catch (e) {
      toast.error(e.response?.data?.detail || "Generazione fallita");
    } finally {
      setGenText(false);
    }
  };

  useEffect(() => {
    if (card.type !== "spell" || !spellQuery.trim()) {
      setSpellResults([]);
      setSearchingSpells(false);
      return undefined;
    }
    const timer = window.setTimeout(async () => {
      setSearchingSpells(true);
      try {
        const res = await api.get("/spells", { params: { q: spellQuery } });
        setSpellResults(res.data.spells || []);
      } catch (error) {
        setSpellResults([]);
      } finally {
        setSearchingSpells(false);
      }
    }, 220);
    return () => window.clearTimeout(timer);
  }, [card.type, spellQuery]);

  const applySpell = async (spellId) => {
    setApplyingSpell(spellId);
    try {
      const res = await api.post(`/spells/${spellId}/apply`);
      set({
        name: res.data.name || card.name,
        description: res.data.description || card.description,
        story: res.data.story || card.story,
        attributes: { ...DEFAULT_ATTRS.spell, ...(res.data.attributes || {}) },
      });
      setSpellQuery(res.data.name || "");
      setSpellResults([]);
      toast.success("Incantesimo applicato dal Grimorio privato");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Impossibile applicare l'incantesimo");
    } finally {
      setApplyingSpell(null);
    }
  };

  useEffect(() => {
    const types = LIBRARY_TYPES_BY_CARD[card.type];
    if (!types || !referenceQuery.trim()) {
      setReferenceResults([]);
      setSearchingReferences(false);
      return undefined;
    }
    const timer = window.setTimeout(async () => {
      setSearchingReferences(true);
      try {
        const res = await api.get("/library", { params: { q: referenceQuery, types } });
        setReferenceResults(res.data.records || []);
      } catch (error) {
        setReferenceResults([]);
      } finally {
        setSearchingReferences(false);
      }
    }, 220);
    return () => window.clearTimeout(timer);
  }, [card.type, referenceQuery]);

  const applyReference = async (referenceId) => {
    setApplyingReference(referenceId);
    try {
      const res = await api.post(`/library/${referenceId}/apply`);
      set({
        name: res.data.name || card.name,
        description: res.data.description || card.description,
        story: res.data.story || card.story,
        attributes: { ...(DEFAULT_ATTRS[card.type] || {}), ...(res.data.attributes || {}) },
        language: res.data.content_language || card.language,
      });
      setReferenceQuery(res.data.name || "");
      setReferenceResults([]);
      toast.success("Contenuto applicato dalla biblioteca privata");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Impossibile applicare il contenuto");
    } finally {
      setApplyingReference(null);
    }
  };

  const showReferenceSource = async (referenceId) => {
    setLoadingSourceRecord(referenceId);
    try {
      const res = await api.get(`/library/${referenceId}`);
      setSourceRecord(res.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Impossibile leggere la fonte del record");
    } finally {
      setLoadingSourceRecord(null);
    }
  };

  const retryReferenceTranslation = async (referenceId) => {
    if (!user?.is_premium) { setPremiumOpen(true); return; }
    setRetryingTranslation(referenceId);
    try {
      const res = await api.post(`/library/${referenceId}/translation-retry`);
      const updatedRecord = res.data;
      const summary = {
        id: updatedRecord.id,
        name: updatedRecord.name,
        reference_type: updatedRecord.reference_type,
        attributes: updatedRecord.attributes || {},
        source_refs: updatedRecord.source_refs || [],
        source_language: updatedRecord.source_language || "it",
        translation_status: updatedRecord.translation_status,
        needs_review: Boolean(updatedRecord.review_flags?.length) || updatedRecord.review_status === "needs_review",
      };
      setSourceRecord((current) => current?.id === referenceId ? updatedRecord : current);
      setReferenceResults((current) => current.map((record) => record.id === referenceId ? { ...record, ...summary } : record));
      if (updatedRecord.translation_status === "translated") {
        toast.success("Traduzione riprovata e completata");
      } else {
        toast.error("La traduzione non è riuscita: il testo sorgente resta da verificare");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Impossibile riprovare la traduzione");
    } finally {
      setRetryingTranslation(null);
    }
  };

  const loadLibraryManuals = useCallback(async () => {
    if (!user?.is_premium) return;
    setLoadingManuals(true);
    try {
      const res = await api.get("/library/manuals");
      const manuals = res.data.manuals || [];
      setLibraryManuals(manuals);
      setSelectedManual((current) => current || manuals[0]?.filename || "");
    } catch (error) {
      setLibraryManuals([]);
    } finally {
      setLoadingManuals(false);
    }
  }, [user?.is_premium]);

  useEffect(() => { loadLibraryManuals(); }, [loadLibraryManuals]);

  const importManual = async () => {
    if (!selectedManual) { toast.error("Seleziona un manuale"); return; }
    if (selectedSpanishManual && !translationConfirmed) {
      toast.error("Conferma l'invio del testo estratto a Gemini per la traduzione");
      return;
    }
    if (useSelectedManualOcr && !ocrConfirmed) {
      toast.error("Conferma l'invio delle pagine selezionate a Gemini per l'OCR");
      return;
    }
    const start = Math.max(1, Number.parseInt(manualStartPage, 10) || 1);
    const end = Math.max(start, Number.parseInt(manualEndPage, 10) || start);
    setManualImporting(true);
    try {
      const res = await api.post("/library/import", {
        filenames: [selectedManual],
        start_page: start,
        ...(selectedSpanishManual ? { end_page: end, translation_processing_confirmed: true } : {}),
        ...(useSelectedManualOcr ? { end_page: end, use_ai_ocr: true, external_processing_confirmed: true } : {}),
      });
      const report = res.data.sources?.[0];
      const translated = report?.translated ? ` · ${report.translated} tradotti in italiano` : "";
      const failed = report?.translation_failed ? ` · ${report.translation_failed} traduzioni da verificare` : "";
      toast.success(`${res.data.imported + res.data.updated} contenuti importati${translated}${failed}${report?.pages_needing_ocr?.length ? ` · ${report.pages_needing_ocr.length} pagine richiedono OCR` : ""}`);
      await loadLibraryManuals();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Importazione del manuale non riuscita");
    } finally {
      setManualImporting(false);
    }
  };

  const generateImage = async () => {
    if (!user?.is_premium) { setPremiumOpen(true); return; }
    const p = card.description.trim() || prompt.trim() || card.story.trim();
    if (!p) { toast.error("Aggiungi un nome o una descrizione prima"); return; }
    setGenImg(true);
    try {
      const res = await api.post("/ai/generate-image", {
        prompt: p,
        type: card.type,
        cleanup: cleanupArtwork,
      });
      set({ artwork_path: res.data.artwork_path });
      if (res.data.cleanup_notice) {
        toast.warning(res.data.cleanup_notice);
      } else {
        toast.success("Artwork evocato");
      }
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
    } else if (t === "armor") {
      let s = `${name} è ${g("categoria") ? g("categoria").toLowerCase() : "un'armatura"}`;
      if (g("classe_armatura")) s += ` con CA ${g("classe_armatura")}`;
      s += ".";
      parts.push(s);
      if (g("forza_minima")) parts.push(`Richiede Forza ${g("forza_minima")}.`);
      if (g("svantaggio_furtivita") && /s[ìi]/i.test(g("svantaggio_furtivita"))) parts.push("Impone svantaggio alle prove di Furtività.");
      if (g("peso") || g("costo")) parts.push([g("peso") && `Peso ${g("peso")}`, g("costo") && `costo ${g("costo")}`].filter(Boolean).join(", ") + ".");
    } else if (t === "item") {
      let s = `${name} è ${g("categoria") ? g("categoria").toLowerCase() : "un oggetto"}`;
      if (g("rarita")) s += ` ${g("rarita").toLowerCase()}`;
      s += ".";
      parts.push(s);
      if (g("sintonia")) parts.push(g("sintonia") + ".");
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
    // Let the browser/Axios add the multipart boundary automatically.
    e.target.value = "";
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await api.post("/upload", fd);
      set({ artwork_path: res.data.artwork_path });
      toast.success("Immagine caricata");
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message = typeof detail === "string" ? detail : "Caricamento immagine fallito";
      toast.error(message);
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
                <p className="mt-2 font-body text-sm text-muted-foreground">Segui i passaggi del laboratorio: la preview resta accanto a te mentre modifichi.</p>
            </div>
             <EditorNavigation />

            {/* Type + language */}
             <div id="editor-identity" className="grid scroll-mt-28 grid-cols-1 sm:grid-cols-2 gap-4">
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

             {card.type === "spell" && (
               <section id="editor-grimoire" className="scroll-mt-28 border border-gold-deep/50 bg-card p-5">
                 <div className="flex items-center gap-2">
                   <BookOpen className="h-4 w-4 text-gold" />
                   <h2 className="font-label text-xs tracking-widest text-gold">GRIMORIO PRIVATO</h2>
                 </div>
                 <p className="mt-2 font-body text-xs leading-relaxed text-muted-foreground">
                   Cerca un incantesimo importato. I suoi dati regolamentari compilano la carta senza usare crediti AI.
                 </p>
                 <div className="relative mt-3">
                   <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-gold/70" />
                   <Input
                     data-testid="spell-search"
                     value={spellQuery}
                     onChange={(event) => setSpellQuery(event.target.value)}
                     placeholder="Es. Palla di fuoco"
                     className={`${inputCls} pl-9`}
                   />
                   {searchingSpells && <Loader2 className="absolute right-3 top-3 h-4 w-4 animate-spin text-gold" />}
                 </div>
                 {spellQuery.trim() && !searchingSpells && spellResults.length === 0 && (
                   <p className="mt-3 font-body text-xs text-muted-foreground">Nessun incantesimo corrispondente nel tuo Grimorio.</p>
                 )}
                 {spellResults.length > 0 && (
                   <div className="mt-3 divide-y divide-border border border-border">
                     {spellResults.map((spell) => (
                       <button
                         key={spell.id}
                         type="button"
                         data-testid={`apply-spell-${spell.id}`}
                         disabled={applyingSpell === spell.id}
                         onClick={() => applySpell(spell.id)}
                         className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left transition-colors hover:bg-secondary disabled:opacity-60"
                       >
                         <span>
                           <span className="block font-heading text-base text-foreground">{spell.name}</span>
                           <span className="mt-0.5 block font-body text-[11px] text-muted-foreground">
                             {spell.level === "Trucchetto" ? spell.level : `${spell.level || "?"}° livello`} · {spell.school || "Scuola non rilevata"} · {(spell.classes || []).join(", ")}
                           </span>
                         </span>
                         {applyingSpell === spell.id
                           ? <Loader2 className="h-4 w-4 shrink-0 animate-spin text-gold" />
                           : <span className="font-label text-[10px] tracking-widest text-gold">APPLICA</span>}
                       </button>
                     ))}
                   </div>
                 )}
               </section>
             )}

              {user?.is_premium && (
                <section id="editor-library-import" className="scroll-mt-28 border border-amber-700/45 bg-amber-950/10 p-5">
                  <div className="flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-amber-300" />
                    <h2 className="font-label text-xs tracking-widest text-amber-200">CUSTODIA DEI MANUALI</h2>
                  </div>
                  <p className="mt-2 font-body text-xs leading-relaxed text-muted-foreground">
                    Importa i riferimenti strutturati dai PDF locali del tuo account. I PDF non vengono caricati nello storage né resi pubblici.
                  </p>
                  <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div>
                      <Label className="font-label text-[10px] tracking-widest text-gold/80">MANUALE</Label>
                      <Select value={selectedManual} onValueChange={setSelectedManual} disabled={loadingManuals || !libraryManuals.length}>
                        <SelectTrigger className={`${inputCls} mt-1`}><SelectValue placeholder="Caricamento manuali…" /></SelectTrigger>
                        <SelectContent className="bg-card border-gold-deep/40 rounded-none">
                          {libraryManuals.map((manual) => (
                            <SelectItem key={manual.filename} value={manual.filename} className="font-body text-xs">
                              {manual.title || manual.filename.replace(/__\d+\.pdf$/, "").replaceAll("_", " ")} · {manual.imported_records} record
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex items-end">
                      <Button type="button" onClick={importManual} disabled={manualImporting || !selectedManual}
                        className="w-full rounded-none bg-amber-700 text-white hover:bg-amber-600 font-label text-xs tracking-wide">
                        {manualImporting ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <BookOpen className="mr-1.5 h-4 w-4" />}
                        {useSelectedManualOcr ? "IMPORTA CON OCR" : "IMPORTA TESTO NATIVO"}
                      </Button>
                    </div>
                  </div>
                   {selectedSpanishManual && (
                     <p className="mt-3 border-l-2 border-sky-500/60 pl-3 font-body text-[11px] leading-relaxed text-sky-100/80">
                       Fonte spagnola con testo nativo: l’importazione non invia pagine a OCR. I record vengono tradotti in italiano in piccoli gruppi e conservano testo, lingua e pagina originali per la revisione.
                     </p>
                   )}
                   {selectedSpanishManual && (
                     <div className="mt-3 flex items-start gap-2 border border-sky-700/40 bg-sky-950/20 p-3">
                       <Switch id="translation-confirmation" checked={translationConfirmed} onCheckedChange={setTranslationConfirmed} />
                       <Label htmlFor="translation-confirmation" className="font-body text-[11px] leading-relaxed text-sky-100/80">
                         Confermo di poter inviare a Gemini il solo testo strutturato estratto (non il PDF né immagini di pagina) per tradurlo in italiano. La lingua, il testo e la pagina originali resteranno disponibili per la revisione.
                       </Label>
                     </div>
                   )}
                  <div className="mt-4 flex items-center justify-between gap-3 border-t border-amber-900/50 pt-4">
                    <div>
                      <Label htmlFor="ocr-enabled" className="font-label text-[10px] tracking-widest text-amber-100">OCR GEMINI PER PAGINE SCANSIONATE</Label>
                       <p className="mt-1 font-body text-[11px] text-muted-foreground">
                         {selectedSpanishManual ? "Non disponibile per la fonte spagnola nativa: nessuna pagina sarà inviata a Gemini." : "Massimo 12 pagine per volta, ripetibile e verificabile."}
                       </p>
                    </div>
                     <Switch
                       id="ocr-enabled"
                       checked={useSelectedManualOcr}
                       disabled={selectedSpanishManual}
                       onCheckedChange={setUseManualOcr}
                     />
                  </div>
                  {(useSelectedManualOcr || selectedSpanishManual) && (
                    <div className="mt-3 space-y-3 border-l-2 border-amber-700/50 pl-3">
                      {selectedSpanishManual && (
                        <p className="font-body text-[11px] leading-relaxed text-sky-100/80">
                          Scegli fino a 12 pagine per volta: l’importazione resta riprendibile e traduce il testo completo dei record rilevati.
                        </p>
                      )}
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Label className="font-label text-[10px] tracking-widest text-gold/80">{selectedSpanishManual ? "DA PAGINA (TRADUZIONE)" : "DA PAGINA"}</Label>
                          <Input type="number" min="1" value={manualStartPage} onChange={(event) => setManualStartPage(event.target.value)} className={`${inputCls} mt-1`} />
                        </div>
                        <div>
                          <Label className="font-label text-[10px] tracking-widest text-gold/80">{selectedSpanishManual ? "A PAGINA (MAX 12)" : "A PAGINA"}</Label>
                          <Input type="number" min="1" value={manualEndPage} onChange={(event) => setManualEndPage(event.target.value)} className={`${inputCls} mt-1`} />
                        </div>
                      </div>
                      {useSelectedManualOcr && <div className="flex items-start gap-2">
                        <Switch id="ocr-confirmation" checked={ocrConfirmed} onCheckedChange={setOcrConfirmed} />
                        <Label htmlFor="ocr-confirmation" className="font-body text-[11px] leading-relaxed text-muted-foreground">
                          Confermo di poter inviare a Gemini esclusivamente le pagine selezionate per trascriverle. Verificherò i record contrassegnati.
                        </Label>
                      </div>}
                    </div>
                  )}
                </section>
              )}

              {LIBRARY_TYPES_BY_CARD[card.type] && (
                <section id="editor-library" className="scroll-mt-28 border border-gold-deep/50 bg-card p-5">
                  <div className="flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-gold" />
                    <h2 className="font-label text-xs tracking-widest text-gold">BIBLIOTECA PRIVATA</h2>
                  </div>
                  <p className="mt-2 font-body text-xs leading-relaxed text-muted-foreground">
                    Cerca contenuti già importati dai tuoi manuali. I dati regolamentari compilano la carta senza usare crediti AI.
                  </p>
                  <div className="relative mt-3">
                    <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-gold/70" />
                    <Input
                      data-testid="reference-search"
                      value={referenceQuery}
                      onChange={(event) => setReferenceQuery(event.target.value)}
                      placeholder={card.type === "class" ? "Es. Guerriero, Arciere Arcano…" : card.type === "monster" ? "Es. Beholder" : "Cerca nella biblioteca"}
                      className={`${inputCls} pl-9`}
                    />
                    {searchingReferences && <Loader2 className="absolute right-3 top-3 h-4 w-4 animate-spin text-gold" />}
                  </div>
                  {referenceQuery.trim() && !searchingReferences && referenceResults.length === 0 && (
                    <p className="mt-3 font-body text-xs text-muted-foreground">Nessun contenuto corrispondente nella tua biblioteca.</p>
                  )}
                  {referenceResults.length > 0 && (
                    <div className="mt-3 divide-y divide-border border border-border">
                      {referenceResults.map((record) => (
                        <div key={record.id} className="flex items-center justify-between gap-3 px-3 py-3 transition-colors hover:bg-secondary">
                          <button
                            type="button"
                            data-testid={`apply-reference-${record.id}`}
                            disabled={applyingReference === record.id}
                            onClick={() => applyReference(record.id)}
                            className="min-w-0 flex-1 text-left disabled:opacity-60"
                          >
                            <span className="block font-heading text-base text-foreground">{record.name}</span>
                            <span className="mt-0.5 block font-body text-[11px] text-muted-foreground">
                              {LIBRARY_TYPE_LABELS[record.reference_type] || "Contenuto"} · {(record.source_refs || []).map((ref) => `${ref.language === "es" ? "Fonte spagnola" : ref.filename} p.${ref.page}`).join(", ")}
                              {record.translation_status === "failed" ? " · Traduzione da verificare" : ""}
                              {record.needs_review && record.translation_status !== "failed" ? " · Da verificare" : ""}
                            </span>
                          </button>
                          <button
                            type="button"
                            data-testid={`source-reference-${record.id}`}
                            disabled={loadingSourceRecord === record.id}
                            onClick={() => showReferenceSource(record.id)}
                            className="shrink-0 font-label text-[10px] tracking-widest text-sky-300 hover:text-sky-100 disabled:opacity-60"
                          >
                            {loadingSourceRecord === record.id ? <Loader2 className="h-4 w-4 animate-spin" /> : "FONTE"}
                          </button>
                          {applyingReference === record.id
                            ? <Loader2 className="h-4 w-4 shrink-0 animate-spin text-gold" />
                            : <span className="font-label text-[10px] tracking-widest text-gold">APPLICA</span>}
                        </div>
                      ))}
                    </div>
                  )}
                  {sourceRecord && (
                    <div data-testid="reference-source-panel" className="mt-3 border border-sky-700/50 bg-sky-950/20 p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-label text-[10px] tracking-widest text-sky-200">FONTE ORIGINALE · {sourceRecord.source_language === "es" ? "SPAGNOLO" : "ITALIANO"}</p>
                          <p className="mt-1 font-heading text-base text-foreground">{sourceRecord.source_name || sourceRecord.name}</p>
                        </div>
                        <div className="flex shrink-0 items-center gap-3">
                          {sourceRecord.translation_status === "failed" && (
                            <button
                              type="button"
                              data-testid={`retry-reference-translation-${sourceRecord.id}`}
                              disabled={retryingTranslation === sourceRecord.id}
                              onClick={() => retryReferenceTranslation(sourceRecord.id)}
                              className="flex items-center gap-1 font-label text-[10px] tracking-widest text-amber-200 hover:text-amber-100 disabled:opacity-60"
                            >
                              {retryingTranslation === sourceRecord.id
                                ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                : "RIPROVA TRADUZIONE"}
                            </button>
                          )}
                          <button type="button" onClick={() => setSourceRecord(null)} className="font-label text-[10px] tracking-widest text-muted-foreground hover:text-foreground">CHIUDI</button>
                        </div>
                      </div>
                      <p className="mt-2 font-body text-[11px] text-muted-foreground">
                        {(sourceRecord.source_refs || []).map((ref) => `${ref.filename} · pagina ${ref.page}`).join(", ")}
                        {sourceRecord.translation_status === "failed" ? ` · Traduzione non riuscita${sourceRecord.translation_error ? ` (${sourceRecord.translation_error})` : ""}: verifica il testo prima di applicarlo.` : ""}
                      </p>
                      <p className="mt-3 whitespace-pre-wrap font-body text-xs leading-relaxed text-foreground/90">{sourceRecord.source_full_text || sourceRecord.source_description || sourceRecord.full_text}</p>
                    </div>
                  )}
                </section>
              )}

            {/* AI generation */}
             <div id="editor-evocation" className="scroll-mt-28 border border-gold-deep/40 bg-card p-5">
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
              <div className="mt-3 flex items-start justify-between gap-4 border border-gold-deep/30 bg-secondary/20 px-3 py-3">
                <div>
                  <Label htmlFor="artwork-cleanup" className="font-label text-[11px] tracking-wider text-gold">
                    PULISCI FIRME E FILIGRANE
                  </Label>
                  <p className="mt-1 font-body text-[11px] leading-relaxed text-muted-foreground">
                    Richiede un passaggio AI aggiuntivo per rimuovere eventuali firme, loghi o testo dall’artwork.
                  </p>
                </div>
                <Switch
                  id="artwork-cleanup"
                  data-testid="artwork-cleanup-switch"
                  checked={cleanupArtwork}
                  onCheckedChange={setCleanupArtwork}
                  disabled={genImg}
                  aria-label="Richiedi la pulizia di firme e filigrane"
                  className="mt-1 data-[state=checked]:bg-gold"
                />
              </div>
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
             <div id="editor-content" className="scroll-mt-28 space-y-5">
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
             <div id="editor-stats" className="scroll-mt-28 border-t border-border pt-6">
              <h2 className="font-heading text-2xl text-foreground mb-4">Statistiche & Attributi</h2>
              <AttributeEditor attributes={card.attributes} onChange={(a) => set({ attributes: a })} allowCustomFields={card.type === "custom"} />
            </div>

             <Accordion type="multiple" defaultValue={["appearance", "back"]} className="border-y border-border">
               <AccordionItem value="appearance" id="editor-appearance" className="scroll-mt-28 border-border">
                 <AccordionTrigger className="font-heading text-xl text-foreground hover:no-underline">
                   <span className="flex items-center gap-2"><Palette className="h-5 w-5 text-gold" /> 4 · ASPETTO DEL FRONTE</span>
                 </AccordionTrigger>
                 <AccordionContent className="pt-2">
                   <CardAppearanceControls
                     frame={card.frame || "gold"}
                     appearance={{ ...DEFAULT_APPEARANCE, ...(card.appearance || {}) }}
                     onFrameChange={(frame) => set({ frame })}
                     onAppearanceChange={setAppearance}
                   />
                 </AccordionContent>
               </AccordionItem>

               <AccordionItem value="back" id="editor-back" className="scroll-mt-28 border-0">
                 <AccordionTrigger className="font-heading text-xl text-foreground hover:no-underline">
                   <span className="flex items-center gap-2"><Palette className="h-5 w-5 text-gold" /> 5 · RETRO DELLA CARTA</span>
                 </AccordionTrigger>
                 <AccordionContent className="pt-2">
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
                 </AccordionContent>
               </AccordionItem>
             </Accordion>

            <Button data-testid="save-btn" onClick={save} disabled={saving}
              className="w-full sm:w-auto rounded-none bg-gold text-obsidian hover:bg-gold-deep font-label tracking-widest h-12 px-10 transition-colors">
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
              {isEdit ? "SALVA MODIFICHE" : "FORGIA LA CARTA"}
            </Button>
          </div>

          {/* PREVIEW */}
            <div className="lg:sticky lg:top-24 h-fit lg:max-h-[calc(100vh-7rem)]">
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

const EditorNavigation = () => {
  const goTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  return (
    <nav aria-label="Passaggi dell'editor" className="grid grid-cols-2 gap-2 border-y border-border py-3 sm:grid-cols-5">
      {[
        ["editor-identity", "1 · IDENTITÀ"],
        ["editor-evocation", "2 · CONTENUTO"],
        ["editor-stats", "3 · STATISTICHE"],
        ["editor-appearance", "4 · FRONTE"],
        ["editor-back", "5 · RETRO"],
      ].map(([id, label]) => (
        <button key={id} type="button" onClick={() => goTo(id)}
          className="border border-border px-2 py-2 font-label text-[9px] tracking-wider text-muted-foreground transition-colors hover:border-gold-deep hover:text-gold sm:text-[10px]">
          {label}
        </button>
      ))}
    </nav>
  );
};
