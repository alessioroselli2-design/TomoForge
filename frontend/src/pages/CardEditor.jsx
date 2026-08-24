import React, { useCallback, useEffect, useState, useRef } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Wand2, ImagePlus, Upload, Save, ArrowLeft, Loader2, Palette, PenLine, Crown, BookOpen, Search, Link2, X, CheckCircle2, XCircle, AlertTriangle, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { CARD_TYPES, EMBLEMS, BACK_STYLES, DEFAULT_APPEARANCE, attrLabel } from "@/lib/cardTypes";
import Navbar from "@/components/Navbar";
import { PremiumDialog } from "@/components/PremiumDialog";
import { CardAppearanceControls } from "@/components/CardAppearanceControls";
import { ReferenceUpdatesPanel } from "@/components/ReferenceUpdatesPanel";
import { CardHistoryPanel } from "@/components/CardHistoryPanel";
import LibraryCoverageReadiness from "@/components/LibraryCoverageReadiness";
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
  subclass: { dado_vita: "", abilita_primaria: "", tiri_salvezza: "", competenze: "", caratteristiche: [] },
  feature: { livello: "", benefici: [] },
  race: { bonus_caratteristiche: "", velocita: "", taglia: "", linguaggi: "", tratti: [] },
  weapon: { danno: "", tipo_danno: "", proprieta: "", gittata: "", peso: "", costo: "", categoria: "" },
  armor: { classe_armatura: "", forza_minima: "", svantaggio_furtivita: "", peso: "", costo: "", categoria: "" },
  item: { categoria: "", costo: "", peso: "", proprieta: "", rarita: "", sintonia: "" },
  feat: { prerequisito: "", benefici: [] },
  monster: { classe_armatura: "", punti_ferita: "", velocita: "", for: "", des: "", cos: "", int: "", sag: "", car: "", tiri_salvezza: "", resistenze: "", vulnerabilita: "", immunita: "", sensi: "", linguaggi: "", grado_sfida: "", azioni: [{ nome: "", descrizione: "" }] },
  character: {
    classe: "", sottoclasse: "", razza: "", sottorazza: "", background: "", livello: "",
    for: "", des: "", cos: "", int: "", sag: "", car: "", bonus_competenza: "",
    classe_armatura: "", punti_ferita: "", pf_attuali: "", pf_temporanei: "", dadi_vita: "",
    velocita: "", taglia: "", iniziativa: "", percezione_passiva: "", ispirazione: "", allineamento: "",
    linguaggi: [], competenze: [], abilita_sottoclasse: [], privilegi: [], tratti_razza: [], talenti: [],
    armi_trucchi: [], equipaggiamento: [], competenza_armature: "", competenze_armi: "", strumenti: "",
    aspetto: "", caratteristica_incantatore: "", modificatore_incantatore: "", cd_incantesimi: "",
    bonus_attacco_incantesimi: "", denari: "", sintonia: [], slot_incantesimi: [], incantesimi: [],
  },
  custom: {},
};

const inputCls = "bg-input border-border rounded-none font-body focus-visible:ring-gold";
const LIBRARY_TYPES_BY_CARD = {
  spell: "spell",
  class: "class,subclass,class_feature",
  subclass: "subclass",
  feature: "class_feature,ability",
  race: "race,subrace",
  feat: "feat",
  monster: "monster",
  weapon: "weapon",
  armor: "armor,shield",
  item: "equipment,tool,magic_item,vehicle,ammunition,mount,trade_good,service,other",
  custom: "ability,other",
  character: "class,subclass,class_feature,spell,feat,race,subrace,weapon,armor,shield,equipment,tool,magic_item,vehicle,ammunition,mount,trade_good,service",
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

const hasUserValue = (value) => {
  if (Array.isArray(value)) return value.some(hasUserValue);
  if (value && typeof value === "object") return Object.values(value).some(hasUserValue);
  return value !== undefined && value !== null && String(value).trim() !== "";
};

const mergeMissingValues = (current = {}, incoming = {}) => {
  const merged = { ...current };
  Object.entries(incoming || {}).forEach(([key, value]) => {
    if (!hasUserValue(merged[key]) && hasUserValue(value)) merged[key] = value;
  });
  return merged;
};

const mergeSourceReferences = (current = [], incoming = []) => {
  const seen = new Set();
  return [...current, ...incoming].filter((reference) => {
    const key = `${reference?.filename || ""}:${reference?.page || ""}:${reference?.language || ""}`;
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const mergeRuleSources = (current = [], incoming = []) => {
  const byId = new Map((current || []).map((source) => [`${source.source_kind}:${source.source_id}`, source]));
  (incoming || []).filter(Boolean).forEach((source) => {
    byId.set(`${source.source_kind}:${source.source_id}`, source);
  });
  return [...byId.values()];
};

const addCharacterReference = (attributes, payload) => {
  const referenceType = payload.reference_type;
  const name = payload.name || "";
  const next = mergeMissingValues(attributes, payload.attributes);
  const addDistinct = (field) => {
    const current = Array.isArray(next[field]) ? next[field] : [];
    if (!current.some((item) => (item.reference_id || item.nome) === (payload.reference_id || name))) {
      next[field] = [...current, { reference_id: payload.reference_id, nome: name, descrizione: payload.description || "" }];
    }
  };
  if (referenceType === "class" && !hasUserValue(next.classe)) next.classe = name;
  if ((referenceType === "race" || referenceType === "subrace") && !hasUserValue(next.razza)) next.razza = name;
  if (referenceType === "subclass" && !hasUserValue(next.sottoclasse)) next.sottoclasse = name;
  if (referenceType === "class_feature" || referenceType === "ability" || referenceType === "feat") addDistinct("privilegi");
  if (referenceType === "spell") addDistinct("incantesimi");
  if (["weapon", "armor", "shield", "equipment", "tool", "magic_item", "vehicle", "ammunition", "mount", "trade_good", "service"].includes(referenceType)) addDistinct("equipaggiamento");
  return next;
};

export default function CardEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const isEdit = !!id;
  const requestedType = searchParams.get("type");
  const requestedReferenceId = searchParams.get("referenceId");
  const requestedReviewTypes = searchParams.get("reviewTypes");
  const requestedReviewManual = searchParams.get("reviewManual");
  const fileRef = useRef(null);
  const [premiumOpen, setPremiumOpen] = useState(false);

  const [card, setCard] = useState({
    type: "spell", custom_type: "", name: "", description: "", story: "",
    language: "it", attributes: { ...DEFAULT_ATTRS.spell }, artwork_path: null,
    frame: "gold", reference_ids: [], spell_ids: [], rule_sources: [], source_refs: [],
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
  const [reviewTypes, setReviewTypes] = useState("");
  const [reviewManual, setReviewManual] = useState("");
  const [referenceResults, setReferenceResults] = useState([]);
  const [searchingReferences, setSearchingReferences] = useState(false);
  const [applyingReference, setApplyingReference] = useState(null);
  const [libraryManuals, setLibraryManuals] = useState([]);
  const [loadingManuals, setLoadingManuals] = useState(false);
  const [retryingTranslation, setRetryingTranslation] = useState(null);
  const [preloadFired, setPreloadFired] = useState(false);
  const [retryingPreload, setRetryingPreload] = useState(null);
  const [sourceRecord, setSourceRecord] = useState(null);
  const [loadingSourceRecord, setLoadingSourceRecord] = useState(null);
  const [reviewingReference, setReviewingReference] = useState(null);
  const [reviewNotes, setReviewNotes] = useState("");
  const [coverageRefreshKey, setCoverageRefreshKey] = useState(0);
  const [characterReferences, setCharacterReferences] = useState([]);
  const [referenceUpdates, setReferenceUpdates] = useState([]);
  const [refreshingReferenceId, setRefreshingReferenceId] = useState(null);
  const [historyBusy, setHistoryBusy] = useState(false);
  const preloadWasActive = useRef(false);

  const hydrateCard = useCallback((savedCard) => ({
    ...savedCard,
    attributes: { ...(DEFAULT_ATTRS[savedCard.type] || {}), ...(savedCard.attributes || {}) },
    reference_ids: savedCard.reference_ids || [],
    spell_ids: savedCard.spell_ids || [],
    rule_sources: savedCard.rule_sources || [],
    source_refs: savedCard.source_refs || [],
    appearance: { ...DEFAULT_APPEARANCE, ...(savedCard.appearance || {}) },
    back: { style: "classic", color: "#7f1d1d", emblem: "flame", motto: "", ...(savedCard.back || {}) },
  }), []);

  const reloadCard = useCallback(async () => {
    try {
      const res = await api.get(`/cards/${id}`);
      setCard(hydrateCard(res.data));
    } catch (e) {
      toast.error("Carta non trovata");
      navigate("/collezione");
    }
  }, [hydrateCard, id, navigate]);

  useEffect(() => {
    if (isEdit) reloadCard();
  }, [isEdit, reloadCard]);

  const loadReferenceUpdates = useCallback(async () => {
    if (!isEdit) return;
    try {
      const response = await api.get(`/cards/${id}/reference-updates`);
      setReferenceUpdates(response.data.updates || []);
    } catch {
      setReferenceUpdates([]);
    }
  }, [id, isEdit]);
  useEffect(() => { loadReferenceUpdates(); }, [loadReferenceUpdates]);

  useEffect(() => {
    if (isEdit || !requestedType || !DEFAULT_ATTRS[requestedType]) return;
    setCard((current) => ({
      ...current,
      type: requestedType,
      attributes: { ...DEFAULT_ATTRS[requestedType] },
    }));
  }, [isEdit, requestedType]);

  useEffect(() => {
    if (isEdit || !requestedReferenceId) return;
    let active = true;
    (async () => {
      try {
        const res = await api.post(`/library/${requestedReferenceId}/apply`);
        if (!active) return;
        const nextType = res.data.card_type || "custom";
        setCard((current) => ({
          ...current,
          type: nextType,
          name: res.data.name || current.name,
          description: res.data.description || current.description,
          story: res.data.story || current.story,
          language: res.data.content_language || current.language,
          attributes: { ...(DEFAULT_ATTRS[nextType] || {}), ...(res.data.attributes || {}) },
          reference_ids: Array.from(new Set([...(current.reference_ids || []), ...(res.data.reference_ids || [])])),
          rule_sources: mergeRuleSources(current.rule_sources, [res.data.rule_source]),
          source_refs: mergeSourceReferences(current.source_refs, res.data.source_refs || []),
        }));
        toast.success("Contenuto della biblioteca pronto per la carta");
      } catch (error) {
        if (active) toast.error(error.response?.data?.detail || "Impossibile preparare il contenuto della biblioteca");
      }
    })();
    return () => { active = false; };
  }, [isEdit, requestedReferenceId]);

  useEffect(() => {
    if (isEdit || !requestedReviewTypes) return;
    setReviewTypes(requestedReviewTypes);
    setReviewManual(requestedReviewManual || "");
    setReferenceQuery("");
    window.setTimeout(() => document.getElementById("editor-library")?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
  }, [isEdit, requestedReviewManual, requestedReviewTypes]);

  useEffect(() => {
    if (card.type !== "character" || !card.reference_ids?.length) {
      setCharacterReferences([]);
      return undefined;
    }
    let active = true;
    Promise.all(card.reference_ids.map((referenceId) => api.get(`/library/${referenceId}`)
      .then((response) => response.data)
      .catch(() => null)))
      .then((records) => { if (active) setCharacterReferences(records.filter(Boolean)); });
    return () => { active = false; };
  }, [card.type, card.reference_ids]);

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
        name: card.name || res.data.name,
        description: card.description || res.data.description,
        story: card.story || res.data.story,
        attributes: mergeMissingValues(card.attributes, res.data.attributes),
        reference_ids: res.data.source === "biblioteca_privata"
          ? Array.from(new Set([...(card.reference_ids || []), ...(res.data.reference_ids || [])]))
          : card.reference_ids,
        spell_ids: res.data.source === "grimorio"
          ? Array.from(new Set([...(card.spell_ids || []), ...(res.data.reference_ids || [])]))
          : card.spell_ids,
        rule_sources: ["biblioteca_privata", "grimorio"].includes(res.data.source)
          ? mergeRuleSources(card.rule_sources, [res.data.rule_source])
          : card.rule_sources,
        source_refs: ["biblioteca_privata", "grimorio"].includes(res.data.source)
          ? mergeSourceReferences(card.source_refs, res.data.source_refs || [])
          : card.source_refs,
      });
      toast.success(
        res.data.source === "grimorio" ? "Dati applicati dal Grimorio privato"
          : res.data.source === "biblioteca_privata" ? "Dati applicati dalla biblioteca privata"
            : "Contenuto evocato dall'arcano"
      );
      if (res.data.source_status === "unavailable") {
        toast.warning(res.data.source_message || "Nessuna fonte verificata è disponibile: il contenuto generato non è una regola certa.");
      }
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
        const res = await api.get("/library", {
          params: {
            q: spellQuery,
            types: "spell",
            include_unverified: true,
          },
        });
        setSpellResults(res.data.records || []);
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
      const res = await api.post(`/library/${spellId}/apply`);
      set({
        name: card.name || res.data.name,
        description: card.description || res.data.description,
        story: card.story || res.data.story,
        attributes: mergeMissingValues(card.attributes, { ...DEFAULT_ATTRS.spell, ...(res.data.attributes || {}) }),
        reference_ids: Array.from(new Set([...(card.reference_ids || []), res.data.reference_id || spellId])),
        rule_sources: mergeRuleSources(card.rule_sources, [res.data.rule_source]),
        source_refs: mergeSourceReferences(card.source_refs, res.data.source_refs || []),
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
    if ((!types && !reviewTypes) || (!referenceQuery.trim() && !reviewTypes)) {
      setReferenceResults([]);
      setSearchingReferences(false);
      return undefined;
    }
    const timer = window.setTimeout(async () => {
      setSearchingReferences(true);
      try {
        const res = await api.get("/library", {
          params: {
            ...(referenceQuery.trim() ? { q: referenceQuery } : {}),
            types: reviewTypes || types,
            ...(reviewTypes ? { review_only: true, include_unverified: true } : {}),
            ...(reviewManual ? { source_filename: reviewManual } : {}),
          },
        });
        setReferenceResults(res.data.records || []);
      } catch (error) {
        setReferenceResults([]);
      } finally {
        setSearchingReferences(false);
      }
    }, 220);
    return () => window.clearTimeout(timer);
  }, [card.type, referenceQuery, reviewManual, reviewTypes]);

  const openCoverageReviews = (types, sourceFilename) => {
    setReviewTypes(types);
    setReviewManual(sourceFilename || "");
    setReferenceQuery("");
    window.setTimeout(() => document.getElementById("editor-library")?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
  };

  const applyReference = async (referenceId) => {
    setApplyingReference(referenceId);
    try {
      const res = await api.post(`/library/${referenceId}/apply`);
      const referenceIds = Array.from(new Set([...(card.reference_ids || []), res.data.reference_id || referenceId]));
      const sourceRefs = mergeSourceReferences(card.source_refs, res.data.source_refs);
      const ruleSources = mergeRuleSources(card.rule_sources, [res.data.rule_source]);
      if (card.type === "character") {
        set({
          attributes: addCharacterReference(card.attributes, res.data),
          reference_ids: referenceIds,
          rule_sources: ruleSources,
          source_refs: sourceRefs,
        });
        setCharacterReferences((current) => current.some((record) => record.id === res.data.reference_id)
          ? current
          : [...current, {
            id: res.data.reference_id || referenceId,
            name: res.data.name,
            reference_type: res.data.reference_type,
            source_refs: res.data.source_refs || [],
          }]);
      } else {
        set({
          name: card.name || res.data.name,
          description: card.description || res.data.description,
          story: card.story || res.data.story,
          attributes: mergeMissingValues(card.attributes, { ...(DEFAULT_ATTRS[card.type] || {}), ...(res.data.attributes || {}) }),
          reference_ids: referenceIds,
          rule_sources: ruleSources,
          source_refs: sourceRefs,
          language: res.data.content_language || card.language,
        });
      }
      setReferenceQuery(res.data.name || "");
      setReferenceResults([]);
      toast.success(card.type === "character" ? "Riferimento aggiunto senza sovrascrivere le tue scelte" : "Contenuto applicato dalla biblioteca privata");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Impossibile applicare il contenuto");
    } finally {
      setApplyingReference(null);
    }
  };

  const removeCharacterReference = (referenceId) => {
    const attributes = { ...card.attributes };
    ["privilegi", "incantesimi", "equipaggiamento"].forEach((field) => {
      if (Array.isArray(attributes[field])) {
        attributes[field] = attributes[field].filter((item) => item?.reference_id !== referenceId);
      }
    });
    set({
      reference_ids: (card.reference_ids || []).filter((id) => id !== referenceId),
      rule_sources: (card.rule_sources || []).filter((source) => source.source_id !== referenceId),
      attributes,
    });
    setCharacterReferences((current) => current.filter((record) => record.id !== referenceId));
  };

  const showReferenceSource = async (referenceId, needsReview = false) => {
    setLoadingSourceRecord(referenceId);
    try {
      // Premium owners can open the private review projection for every
      // record, including already verified translations, so the audit trail
      // remains visible after the decision removes the review flag.
      const res = await api.get(`/library/${referenceId}${user?.is_premium ? "/review" : (needsReview ? "/review" : "")}`);
      setSourceRecord(res.data);
      setReviewNotes(res.data.review_notes || "");
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
        source_name: updatedRecord.source_name || "",
        source_language: updatedRecord.source_language || "it",
        translation_status: updatedRecord.translation_status,
        review_status: updatedRecord.review_status,
        review_notes: updatedRecord.review_notes || "",
        needs_review: updatedRecord.needs_review,
        review_reason: updatedRecord.review_reason,
        review_state: updatedRecord.review_state,
        is_trusted: updatedRecord.is_trusted,
      };
      setSourceRecord((current) => current?.id === referenceId ? updatedRecord : current);
      setReferenceResults((current) => current.map((record) => record.id === referenceId ? { ...record, ...summary } : record));
      setReviewNotes(updatedRecord.review_notes || "");
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

  const reviewReference = async (reviewStatus) => {
    if (!sourceRecord?.id) return;
    setReviewingReference(reviewStatus);
    try {
      const response = await api.patch(`/library/${sourceRecord.id}/review`, {
        review_status: reviewStatus,
        review_notes: reviewNotes.trim(),
      });
      const updatedRecord = response.data;
      setSourceRecord(updatedRecord);
      setReviewNotes(updatedRecord.review_notes || "");
      setCoverageRefreshKey((current) => current + 1);
      if (reviewStatus === "verified") {
        setReferenceResults((current) => current.filter((record) => record.id !== updatedRecord.id));
        toast.success("Traduzione confermata: il record è ora utilizzabile");
      } else {
        setReferenceResults((current) => current.map((record) => (
          record.id === updatedRecord.id
            ? { ...record, ...updatedRecord, needs_review: true, is_trusted: false }
            : record
        )));
        toast.success("Record mantenuto in revisione con la tua nota");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Impossibile salvare la revisione");
    } finally {
      setReviewingReference(null);
    }
  };

  const refreshReference = async (referenceId, isUntracked) => {
    if (!window.confirm(
      "L’aggiornamento usa l’ultima versione salvata della carta. Salva prima eventuali modifiche manuali non ancora salvate. Continuare?"
    )) return;
    setRefreshingReferenceId(referenceId);
    try {
      const response = await api.post(`/cards/${id}/reference-updates`, { reference_ids: [referenceId], version: card.version });
      const refreshedCard = response.data.card;
      setCard(hydrateCard(refreshedCard));
      await loadReferenceUpdates();
      const protectedCount = (response.data.protected_fields?.[referenceId] || []).length;
      if (isUntracked) {
        toast.success("Istantanea della fonte fissata: nessun dato della carta è stato cambiato");
      } else if (protectedCount) {
        toast.success(`Fonte aggiornata: ${protectedCount} valori manuali sono rimasti invariati`);
      } else {
        toast.success("Dati derivati aggiornati dalla fonte corrente");
      }
    } catch (error) {
      if (error.response?.status === 409) {
        await reloadCard();
        toast.error("La scheda era cambiata in un’altra schermata: ho ricaricato la versione salvata. Verifica i dati prima di riprovare.");
      } else {
        toast.error(error.response?.data?.detail || "Impossibile aggiornare la fonte collegata");
      }
    } finally {
      setRefreshingReferenceId(null);
    }
  };

  const restoreHistory = async (action) => {
    setHistoryBusy(true);
    try {
      const response = await api.post(`/cards/${id}/history/${action}`, { version: card.version });
      const restoredCard = response.data.card;
      setCard(hydrateCard(restoredCard));
      await loadReferenceUpdates();
      toast.success(action === "undo" ? "Ultima modifica annullata" : "Modifica ripristinata");
    } catch (error) {
      if (error.response?.status === 409) {
        await reloadCard();
        toast.error("La scheda era cambiata in un’altra schermata: ho ricaricato la versione salvata. Verifica i dati prima di riprovare.");
      } else {
        toast.error(error.response?.data?.detail || "Impossibile aggiornare la cronologia");
      }
    } finally {
      setHistoryBusy(false);
    }
  };

  const loadLibraryManuals = useCallback(async () => {
    if (!user?.is_premium) return;
    setLoadingManuals(true);
    try {
      const res = await api.get("/library/manuals");
      setLibraryManuals(res.data.manuals || []);
    } catch {
      setLibraryManuals([]);
    } finally {
      setLoadingManuals(false);
    }
  }, [user?.is_premium]);

  useEffect(() => { loadLibraryManuals(); }, [loadLibraryManuals]);

  // Auto-fire preload once after manuals are loaded for premium users
  useEffect(() => {
    if (!user?.is_premium || preloadFired || loadingManuals) return;
    if (libraryManuals.length === 0) return;
    setPreloadFired(true);
    api.post("/library/preload")
      .then((response) => {
        if (Array.isArray(response.data?.manuals)) {
          setLibraryManuals(response.data.manuals);
          setCoverageRefreshKey((current) => current + 1);
        }
      })
      .catch(() => {});
  }, [user?.is_premium, preloadFired, loadingManuals, libraryManuals.length]);

  // Poll while any manual job is active OR has unresolved pending translations
  // (so the badge disappears as soon as the user verifies the last pending record).
  useEffect(() => {
    const active = libraryManuals.some(
      (m) =>
        (m.job && (m.job.status === "queued" || m.job.status === "processing")) ||
        (m.records_translation_pending > 0)
    );
    if (!active) return undefined;
    const id = window.setTimeout(() => { loadLibraryManuals(); }, 3000);
    return () => window.clearTimeout(id);
  }, [libraryManuals, loadLibraryManuals]);

  useEffect(() => {
    const active = libraryManuals.some((manual) => ["queued", "processing"].includes(manual.job?.status));
    if (preloadWasActive.current && !active) setCoverageRefreshKey((current) => current + 1);
    preloadWasActive.current = active;
  }, [libraryManuals]);

  const firePreloadForManual = async (filename, opts = {}) => {
    setRetryingPreload(filename);
    try {
      await api.post("/library/preload", { filename, ...opts });
      await loadLibraryManuals();
      setCoverageRefreshKey((current) => current + 1);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Precaricamento non avviato");
    } finally {
      setRetryingPreload(null);
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
        reference_ids: card.reference_ids || [], spell_ids: card.spell_ids || [], rule_sources: card.rule_sources || [], source_refs: card.source_refs || [],
        version: card.version,
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
      if (e.response?.status === 409) {
        await reloadCard();
        toast.error("La scheda era cambiata in un’altra schermata: ho ricaricato la versione salvata. Verifica i dati prima di riprovare.");
      } else {
        toast.error(e.response?.data?.detail || "Salvataggio fallito");
      }
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

            <ReferenceUpdatesPanel
              updates={referenceUpdates}
              refreshingReferenceId={refreshingReferenceId}
              onRefresh={refreshReference}
            />
            <CardHistoryPanel
              history={card.change_history || []}
              busy={historyBusy}
              onUndo={() => restoreHistory("undo")}
              onRedo={() => restoreHistory("redo")}
            />

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
                      {spellResults.map((spell) => {
                        const attributes = spell.attributes || {};
                        const level = spell.level || attributes.livello || "";
                        const school = spell.school || attributes.scuola || "";
                        const classes = spell.classes || attributes.classi || [];
                        return (
                        <button
                         key={spell.id}
                         type="button"
                         data-testid={`apply-spell-${spell.id}`}
                         disabled={applyingSpell === spell.id || spell.is_trusted === false}
                         onClick={() => applySpell(spell.id)}
                         className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left transition-colors hover:bg-secondary disabled:opacity-60"
                       >
                         <span>
                           <span className="block font-heading text-base text-foreground">{spell.name}</span>
                           <span className="mt-0.5 block font-body text-[11px] text-muted-foreground">
                              {level === "Trucchetto" ? level : `${level || "?"}° livello`} · {school || "Scuola non rilevata"}{classes.length > 0 && ` · ${classes.join(", ")}`}
                           </span>
                           <span className="mt-1 block font-body text-[11px] text-sky-100/75">
                             {(spell.source_refs || []).map((ref) => `${ref.filename || "Manuale"} p.${ref.page || "?"}`).join(" · ")}
                             {spell.is_trusted === false && ` · BLOCCATO: ${spell.review_reason || "da verificare"}`}
                           </span>
                         </span>
                         {applyingSpell === spell.id
                           ? <Loader2 className="h-4 w-4 shrink-0 animate-spin text-gold" />
                           : <span className={`font-label text-[10px] tracking-widest ${spell.is_trusted === false ? "text-amber-200" : "text-gold"}`}>{spell.is_trusted === false ? "BLOCCATO" : "APPLICA"}</span>}
                       </button>
                        );
                      })}
                   </div>
                 )}
               </section>
             )}

              {user?.is_premium && (
                 <ManualPreloadDashboard
                   manuals={libraryManuals}
                   loading={loadingManuals}
                   retryingPreload={retryingPreload}
                   onRetry={firePreloadForManual}
                   onOpenReviews={openCoverageReviews}
                 />
               )}

              {user?.is_premium && (
                <LibraryCoverageReadiness onOpenReviews={openCoverageReviews} refreshKey={coverageRefreshKey} />
              )}

              {LIBRARY_TYPES_BY_CARD[card.type] && (
                <section id="editor-library" className="scroll-mt-28 border border-gold-deep/50 bg-card p-5">
                  <div className="flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-gold" />
                    <h2 className="font-label text-xs tracking-widest text-gold">{card.type === "character" ? "BASE NORMATIVA DEL PERSONAGGIO" : "BIBLIOTECA PRIVATA"}</h2>
                  </div>
                  <p className="mt-2 font-body text-xs leading-relaxed text-muted-foreground">
                    {card.type === "character"
                      ? "Aggiungi razza, classe, sottoclasse, privilegi, incantesimi ed equipaggiamento dai manuali importati. Le tue scelte e i tuoi tiri restano prioritari."
                      : "Cerca contenuti già importati dai tuoi manuali. I dati regolamentari compilano la carta senza usare crediti AI."}
                  </p>
                  {card.type === "character" && characterReferences.length > 0 && (
                    <div data-testid="character-references" className="mt-3 border border-sky-700/40 bg-sky-950/20 p-3">
                      <p className="flex items-center gap-1.5 font-label text-[10px] tracking-widest text-sky-200"><Link2 className="h-3.5 w-3.5" /> RIFERIMENTI COLLEGATI</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {characterReferences.map((record) => (
                          <span key={record.id} className="inline-flex items-center gap-1 border border-sky-700/50 bg-obsidian/40 px-2 py-1 font-body text-xs text-sky-100">
                            {LIBRARY_TYPE_LABELS[record.reference_type] || "Contenuto"} · {record.name}
                            <button type="button" aria-label={`Rimuovi ${record.name}`} onClick={() => removeCharacterReference(record.id)} className="text-sky-300 hover:text-crimson">
                              <X className="h-3 w-3" />
                            </button>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="relative mt-3">
                    <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-gold/70" />
                    <Input
                      data-testid="reference-search"
                      value={referenceQuery}
                      onChange={(event) => { setReferenceQuery(event.target.value); setReviewTypes(""); setReviewManual(""); }}
                      placeholder={card.type === "class" ? "Es. Guerriero, Arciere Arcano…" : card.type === "monster" ? "Es. Beholder" : "Cerca nella biblioteca"}
                      className={`${inputCls} pl-9`}
                    />
                    {searchingReferences && <Loader2 className="absolute right-3 top-3 h-4 w-4 animate-spin text-gold" />}
                  </div>
                  {reviewTypes && (
                    <p className="mt-2 flex items-center justify-between border-l-2 border-amber-500/70 bg-amber-950/20 px-3 py-2 font-body text-[11px] text-amber-100/80">
                      <span>Record del tuo account contrassegnati per revisione.</span>
                      <button type="button" onClick={() => { setReviewTypes(""); setReviewManual(""); }} className="font-label text-[9px] tracking-widest text-gold hover:text-amber-200">MOSTRA TUTTI</button>
                    </p>
                  )}
                  {(referenceQuery.trim() || reviewTypes) && !searchingReferences && referenceResults.length === 0 && (
                    <p className="mt-3 font-body text-xs text-muted-foreground">
                      {reviewTypes ? "Nessun record da verificare per queste categorie." : "Nessun contenuto corrispondente nella tua biblioteca."}
                    </p>
                  )}
                  {referenceResults.length > 0 && (
                    <div className="mt-3 divide-y divide-border border border-border">
                      {referenceResults.map((record) => (
                        <div key={record.id} className="flex items-center justify-between gap-3 px-3 py-3 transition-colors hover:bg-secondary">
                          <button
                            type="button"
                            data-testid={`apply-reference-${record.id}`}
                            disabled={applyingReference === record.id || record.is_trusted === false}
                            onClick={() => applyReference(record.id)}
                            className="min-w-0 flex-1 text-left disabled:opacity-60"
                          >
                            <span className="block font-heading text-base text-foreground">{record.name}</span>
                            <span className="mt-0.5 block font-body text-[11px] text-muted-foreground">
                              {LIBRARY_TYPE_LABELS[record.reference_type] || "Contenuto"} · {(record.source_refs || []).map((ref) => `${ref.language === "es" ? "Fonte spagnola" : ref.filename} p.${ref.page}`).join(", ")}
                              {record.source_language === "es" && record.source_name ? ` · Originale: ${record.source_name}` : ""}
                              {record.is_trusted === false ? ` · BLOCCATO: ${record.review_reason || "da verificare"}` : " · Fonte verificata"}
                            </span>
                          </button>
                          <button
                            type="button"
                            data-testid={`source-reference-${record.id}`}
                            disabled={loadingSourceRecord === record.id}
                            onClick={() => showReferenceSource(record.id, record.needs_review)}
                            className="shrink-0 font-label text-[10px] tracking-widest text-sky-300 hover:text-sky-100 disabled:opacity-60"
                          >
                            {loadingSourceRecord === record.id ? <Loader2 className="h-4 w-4 animate-spin" /> : "FONTE"}
                          </button>
                          {applyingReference === record.id
                            ? <Loader2 className="h-4 w-4 shrink-0 animate-spin text-gold" />
                            : <span className={`font-label text-[10px] tracking-widest ${record.is_trusted === false ? "text-amber-200" : "text-gold"}`}>
                              {record.is_trusted === false ? "BLOCCATO" : card.type === "character" ? "AGGIUNGI" : "APPLICA"}
                            </span>}
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
                          {sourceRecord.translation_status === "failed" && sourceRecord.review_status !== "verified" && (
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
                        {sourceRecord.is_trusted === false
                          ? ` · BLOCCATO: ${sourceRecord.review_reason || "verifica necessaria prima dell'uso."}`
                          : " · Fonte verificata e utilizzabile."}
                      </p>
                      {sourceRecord.translation_status === "failed" && sourceRecord.review_status === "verified" && (
                        <p
                          data-testid="translation-failed-verified-notice"
                          className="mt-2 flex items-start gap-1.5 font-body text-[11px] leading-relaxed text-amber-200/80"
                        >
                          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
                          La traduzione automatica ha avuto un errore ma il tuo contenuto manuale è confermato.
                        </p>
                      )}
                      {sourceRecord.needs_review && (
                        <div data-testid="reference-review-panel" className="mt-4 border-t border-sky-700/50 pt-4">
                          <div className="mb-3 flex items-center justify-between gap-3">
                            <p className="font-label text-[10px] tracking-widest text-amber-200">{sourceRecord.source_language === "es" ? "REVISIONE DELLA TRADUZIONE" : "REVISIONE DEL CONTENUTO"}</p>
                            <span className="font-body text-[11px] text-amber-100/70">Il record resta bloccato finché non lo confermi.</span>
                          </div>
                          <div className="grid gap-3 lg:grid-cols-2">
                            <article data-testid="reference-original" className="border border-amber-700/40 bg-amber-950/15 p-3">
                              <p className="font-label text-[9px] tracking-widest text-amber-200">ORIGINALE · {sourceRecord.source_language === "es" ? "SPAGNOLO" : "FONTE"}</p>
                              <h3 className="mt-1 font-heading text-base text-foreground">{sourceRecord.original?.name || sourceRecord.source_name || "Testo originale"}</h3>
                              <p className="mt-2 whitespace-pre-wrap font-body text-xs leading-relaxed text-foreground/85">{sourceRecord.original?.full_text || sourceRecord.source_full_text || "Testo originale non disponibile."}</p>
                            </article>
                            <article data-testid="reference-translation" className="border border-sky-700/40 bg-sky-950/15 p-3">
                              <p className="font-label text-[9px] tracking-widest text-sky-200">TRADUZIONE · ITALIANO</p>
                              <h3 className="mt-1 font-heading text-base text-foreground">{sourceRecord.translation?.name || sourceRecord.name}</h3>
                              <p className="mt-2 whitespace-pre-wrap font-body text-xs leading-relaxed text-foreground/85">{sourceRecord.translation?.full_text || sourceRecord.full_text || "Traduzione non disponibile."}</p>
                            </article>
                          </div>
                          <label className="mt-3 block font-label text-[9px] tracking-widest text-muted-foreground" htmlFor={`review-notes-${sourceRecord.id}`}>NOTA DELLA REVISIONE</label>
                          <Textarea
                            id={`review-notes-${sourceRecord.id}`}
                            data-testid="reference-review-notes"
                            value={reviewNotes}
                            onChange={(event) => setReviewNotes(event.target.value)}
                            placeholder="Indica cosa hai verificato o cosa deve essere corretto…"
                            maxLength={3000}
                            className={`${inputCls} mt-1 min-h-[72px]`}
                          />
                          <div className="mt-3 flex flex-wrap gap-2">
                            <Button
                              type="button"
                              data-testid="approve-reference"
                              disabled={reviewingReference !== null}
                              onClick={() => reviewReference("verified")}
                              className="rounded-none bg-emerald-700 font-label text-[10px] tracking-widest text-white hover:bg-emerald-600"
                            >
                              {reviewingReference === "verified" ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />}
                              {sourceRecord.source_language === "es" ? "CONFERMA TRADUZIONE" : "CONFERMA CONTENUTO"}
                            </Button>
                            <Button
                              type="button"
                              data-testid="reject-reference"
                              disabled={reviewingReference !== null}
                              onClick={() => reviewReference("needs_review")}
                              variant="outline"
                              className="rounded-none border-crimson/60 bg-transparent font-label text-[10px] tracking-widest text-red-200 hover:bg-crimson/15"
                            >
                              {reviewingReference === "needs_review" ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <XCircle className="mr-1.5 h-3.5 w-3.5" />}
                              {sourceRecord.source_language === "es" ? "RIFIUTA TRADUZIONE" : "RIFIUTA CONTENUTO"}
                            </Button>
                          </div>
                        </div>
                      )}
                      <div data-testid="reference-review-history" className="mt-4 border-t border-sky-700/30 pt-3">
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-label text-[9px] tracking-widest text-sky-200">CRONOLOGIA DELLE VERIFICHE</p>
                          <span className="font-body text-[10px] text-muted-foreground">
                            {(sourceRecord.review_history || []).length} {(sourceRecord.review_history || []).length === 1 ? "decisione" : "decisioni"}
                          </span>
                        </div>
                        {(sourceRecord.review_history || []).length === 0 ? (
                          <p className="mt-2 font-body text-xs text-muted-foreground">Nessuna verifica registrata per questo record.</p>
                        ) : (
                          <div className="mt-2 space-y-2">
                            {(sourceRecord.review_history || []).map((entry, index) => {
                              const verified = entry.review_status === "verified";
                              const reviewer = entry.reviewer_name || entry.reviewer_email || "Proprietario";
                              const reviewedAt = entry.reviewed_at
                                ? new Date(entry.reviewed_at).toLocaleString("it-IT", { dateStyle: "medium", timeStyle: "short" })
                                : "Data non disponibile";
                              return (
                                <article
                                  key={`${entry.reviewed_at || "review"}-${index}`}
                                  className="border border-border/70 bg-background/30 px-3 py-2"
                                >
                                  <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                                    <span className={`font-label text-[9px] tracking-widest ${verified ? "text-emerald-300" : "text-amber-200"}`}>
                                      {verified ? "CONFERMATA" : "DA RIVEDERE"}
                                    </span>
                                    <time dateTime={entry.reviewed_at || undefined} className="font-body text-[10px] text-muted-foreground">{reviewedAt}</time>
                                  </div>
                                  <p className="mt-1 font-body text-[11px] text-foreground/85">
                                    {reviewer}{entry.reviewer_email && entry.reviewer_email !== reviewer ? ` · ${entry.reviewer_email}` : ""}
                                  </p>
                                  {entry.review_notes && (
                                    <p className="mt-1 whitespace-pre-wrap font-body text-xs leading-relaxed text-muted-foreground">{entry.review_notes}</p>
                                  )}
                                </article>
                              );
                            })}
                          </div>
                        )}
                      </div>
                      <p className="mt-3 font-body text-xs leading-relaxed text-muted-foreground">
                        Questo confronto è visibile solo al proprietario autenticato del manuale. PDF e immagini di pagina restano privati.
                      </p>
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
              {showBack ? <CardBack card={card} /> : <CardFront card={card} editorMode />}
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

// ─── Manual Preload Dashboard ────────────────────────────────────────────────
// Shows auto-preload status per manual. Fires POST /library/preload once on
// mount (handled in parent). Translation and OCR start automatically. When a
// job has failed, a retry button re-fires POST /library/preload.
// SOURCE PDFs ARE NEVER SHOWN OR UPLOADED.

const JOB_STATUS_LABEL = {
  queued: "IN CODA",
  processing: "ELABORAZIONE IN CORSO",
  completed: "COMPLETATO",
  failed: "ERRORE",
};

/**
 * Shows a live countdown to the next translation retry when the provider has
 * rate-limited the job. Refreshes every second; clears automatically when
 * retryAt is not set or is already in the past.
 */
function TranslationRetryCountdown({ retryAt, attempt }) {
  const [secsLeft, setSecsLeft] = useState(() => {
    if (!retryAt) return null;
    return Math.max(0, Math.round((new Date(retryAt) - Date.now()) / 1000));
  });

  useEffect(() => {
    if (!retryAt) { setSecsLeft(null); return; }
    const tick = () => {
      const s = Math.max(0, Math.round((new Date(retryAt) - Date.now()) / 1000));
      setSecsLeft(s);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [retryAt]);

  if (secsLeft === null) return null;

  return (
    <div
      data-testid="translation-retry-countdown"
      className="mt-2 flex items-center gap-2 border border-amber-800/50 bg-amber-950/15 px-2 py-1.5"
    >
      <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-amber-300" />
      <p className="font-body text-[11px] text-amber-200">
        {secsLeft > 0
          ? `Traduzione in ripresa, prossimo tentativo tra ${secsLeft}s`
          : "Traduzione in ripresa…"}
        {attempt > 0 ? ` (tentativo ${attempt})` : ""}
      </p>
    </div>
  );
}

const JOB_STATUS_COLOR = {
  queued: "text-sky-300",
  processing: "text-amber-200",
  completed: "text-emerald-300",
  failed: "text-red-300",
};

function preloadFailureMessage(lastError) {
  if (String(lastError || "").startsWith("manual_source_duplicate:")) {
    return "Il file fornito non è il Manuale dei Mostri: è una copia del Manuale del Giocatore. Sostituiscilo con il PDF corretto; il precaricamento ripartirà automaticamente.";
  }
  return lastError || "Errore durante il precaricamento. Riprova.";
}

function ManualPreloadDashboard({ manuals, loading, retryingPreload, onRetry, onOpenReviews }) {
  if (loading && !manuals.length) {
    return (
      <section data-testid="preload-dashboard-loading" className="scroll-mt-28 border border-amber-700/40 bg-amber-950/10 p-5">
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin text-amber-300" />
          <h2 className="font-label text-xs tracking-widest text-amber-200">PRECARICAMENTO MANUALI</h2>
        </div>
        <div className="mt-3 h-3 w-48 animate-pulse bg-secondary" />
      </section>
    );
  }

  if (!manuals.length) return null;

  return (
    <section id="editor-library-import" data-testid="preload-dashboard" className="scroll-mt-28 border border-amber-700/45 bg-amber-950/10 p-5">
      <div className="flex items-center gap-2">
        <BookOpen className="h-4 w-4 text-amber-300" />
        <h2 className="font-label text-xs tracking-widest text-amber-200">PRECARICAMENTO AUTOMATICO DEI MANUALI</h2>
      </div>
      <p className="mt-2 font-body text-xs leading-relaxed text-muted-foreground">
        I riferimenti strutturati vengono estratti, tradotti e indicizzati automaticamente dai manuali privati del tuo account.
        Non devi selezionare pagine o confermare passaggi: qui puoi solo seguire l’avanzamento e riprovare un errore.
      </p>

      <div className="mt-4 space-y-3">
        {manuals.map((manual) => {
          const job = manual.job || {};
          const isSpanish = manual.source_language === "es";
          const needsOcr = manual.requires_ocr;
          const isActive = job.status === "queued" || job.status === "processing";
          const isFailed = job.status === "failed";
          const isDone = job.status === "completed";
          const needsSourceReplacement = String(job.last_error || "").startsWith("manual_source_duplicate:");
          const percent = Number(job.percent || 0);
          const title = manual.title || manual.filename.replace(/__\d+\.pdf$/, "").replaceAll("_", " ");

          return (
            <div key={manual.filename} data-testid={`preload-manual-${manual.filename}`} className="border border-amber-700/35 bg-obsidian/35 p-3">
              {/* Header */}
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-heading text-sm text-foreground">{title}</p>
                  <p className="mt-0.5 font-body text-[11px] text-muted-foreground">
                    {isSpanish ? "Testo nativo spagnolo · traduzione automatica" : needsOcr ? "Scansione OCR richiesta" : "Testo nativo"}
                    {manual.page_count ? ` · ${manual.page_count} pagine` : ""}
                  </p>
                </div>
                {job.status && (
                  <span className={`font-label text-[10px] tracking-widest ${JOB_STATUS_COLOR[job.status] || "text-muted-foreground"}`}>
                    {JOB_STATUS_LABEL[job.status] || job.status.toUpperCase()}
                  </span>
                )}
              </div>

              {/* Progress bar */}
              {(isActive || isDone) && (
                <div className="mt-2">
                  <div className="h-1.5 overflow-hidden bg-secondary" aria-label="Avanzamento precaricamento">
                    <div
                      className={`h-full transition-all ${isActive ? "bg-amber-500" : "bg-emerald-500"}`}
                      style={{ width: `${isDone ? 100 : percent}%` }}
                    />
                  </div>
                  {isActive && (
                    <p className="mt-1 font-body text-[11px] text-muted-foreground">
                      {job.current_page && job.page_count ? `Pagina ${job.current_page}/${job.page_count}` : `${percent}%`}
                      {job.records_imported ? ` · ${job.records_imported} importati` : ""}
                      {job.records_updated ? ` · ${job.records_updated} aggiornati` : ""}
                    </p>
                  )}
                </div>
              )}

              {/* Done stats */}
              {isDone && (
                <div className="mt-2 grid grid-cols-2 gap-1.5 sm:grid-cols-4">
                  <div className="border border-emerald-800/50 bg-emerald-950/20 px-2 py-1.5">
                    <p className="font-label text-[9px] tracking-widest text-emerald-300">IMPORTATI</p>
                    <p className="mt-0.5 font-heading text-lg text-foreground">{job.records_imported || 0}</p>
                  </div>
                  <div className="border border-sky-800/50 bg-sky-950/20 px-2 py-1.5">
                    <p className="font-label text-[9px] tracking-widest text-sky-200">AGGIORNATI</p>
                    <p className="mt-0.5 font-heading text-lg text-foreground">{job.records_updated || 0}</p>
                  </div>
                  <div className="border border-amber-800/50 bg-amber-950/20 px-2 py-1.5">
                    <p className="font-label text-[9px] tracking-widest text-amber-200">DA VERIFICARE</p>
                    <p className="mt-0.5 font-heading text-lg text-foreground">{job.records_flagged || 0}</p>
                  </div>
                  {Array.isArray(job.pages_needing_ocr) && job.pages_needing_ocr.length > 0 && (
                    <div className="border border-red-900/60 bg-red-950/20 px-2 py-1.5">
                      <p className="font-label text-[9px] tracking-widest text-red-300">PAGINE OCR MANCANTI</p>
                      <p className="mt-0.5 font-heading text-lg text-foreground">{job.pages_needing_ocr.length}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Translation pending badge — shown on completed jobs when records
                  exhausted all automatic retries and need manual verification */}
              {isDone && manual.records_translation_pending > 0 && (
                <div
                  data-testid={`translation-pending-badge-${manual.filename}`}
                  className="mt-2 flex items-start gap-2 border border-amber-700/60 bg-amber-950/20 px-2 py-1.5"
                >
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-300" />
                  <div className="flex-1">
                    <p className="font-label text-[9px] tracking-widest text-amber-300">
                      TRADUZIONE IN ATTESA — {manual.records_translation_pending}{" "}
                      {manual.records_translation_pending === 1 ? "RECORD" : "RECORD"}
                    </p>
                    <p className="mt-0.5 font-body text-[11px] text-amber-200/80">
                      {manual.records_translation_pending}{" "}
                      {manual.records_translation_pending === 1
                        ? "record non è stato tradotto automaticamente"
                        : "record non sono stati tradotti automaticamente"}
                      {" — "}
                      verificali manualmente per renderli disponibili.
                    </p>
                  </div>
                </div>
              )}

              {/* Translation rate-limit countdown */}
              {job.translation_retry_at && (
                <TranslationRetryCountdown
                  retryAt={job.translation_retry_at}
                  attempt={job.translation_retry_attempt || 0}
                />
              )}

              {/* Failed error */}
              {isFailed && (
                <div className="mt-2 flex items-start gap-2 border border-red-900/50 bg-red-950/15 p-2">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-red-300" />
                  <div className="flex-1">
                    <p className="font-body text-[11px] text-red-200">{preloadFailureMessage(job.last_error)}</p>
                  </div>
                </div>
              )}

              {/* Retry button when failed */}
              {isFailed && !needsSourceReplacement && (
                <Button
                  type="button"
                  data-testid={`retry-preload-${manual.filename}`}
                  disabled={retryingPreload === manual.filename}
                  onClick={() => onRetry(manual.filename, {
                    retry: true,
                  })}
                  className="mt-2 rounded-none bg-amber-700 font-label text-[10px] tracking-widest text-white hover:bg-amber-600"
                >
                  {retryingPreload === manual.filename
                    ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    : <RefreshCw className="mr-1.5 h-3.5 w-3.5" />}
                  RIPROVA PRECARICAMENTO
                </Button>
              )}

              {/* Open review records when done and there are flagged or
                  translation-pending items — guides the user to the review
                  queue so they can complete the library. */}
              {isDone && (job.records_flagged > 0 || manual.records_translation_pending > 0) && (
                <button
                  type="button"
                  data-testid={`open-preload-reviews-${manual.filename}`}
                  onClick={() => onOpenReviews(Object.keys(LIBRARY_TYPE_LABELS).join(","), manual.filename)}
                  className="mt-2 block font-label text-[10px] tracking-widest text-gold hover:text-amber-200"
                >
                  COMPLETA LA REVISIONE
                </button>
              )}
            </div>
          );
        })}
      </div>
    </section>
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
