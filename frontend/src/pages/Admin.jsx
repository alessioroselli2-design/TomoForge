import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Crown, ShieldCheck, Loader2, BookOpenCheck, Languages, Play } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";

export default function Admin() {
  const navigate = useNavigate();
  const { user, loading } = useAuth();
  const [users, setUsers] = useState([]);
  const [busy, setBusy] = useState(true);
  const [q, setQ] = useState("");
  const [ownerUserId, setOwnerUserId] = useState("");
  const [batchSize, setBatchSize] = useState(5);
  const [retryBatchSize, setRetryBatchSize] = useState(5);
  const [retryStatus, setRetryStatus] = useState(null);
  const [retryBusy, setRetryBusy] = useState(false);
  const [retryStatusBusy, setRetryStatusBusy] = useState(false);
  const [translationBatchSize, setTranslationBatchSize] = useState(5);
  const [translationStatus, setTranslationStatus] = useState(null);
  const [translationBusy, setTranslationBusy] = useState(false);
  const [translationStatusBusy, setTranslationStatusBusy] = useState(false);
  const [canonicalStatus, setCanonicalStatus] = useState(null);
  const [canonicalBusy, setCanonicalBusy] = useState(false);
  const [canonicalStatusBusy, setCanonicalStatusBusy] = useState(false);

  useEffect(() => {
    if (!loading && (!user || !user.is_admin)) {
      navigate("/collezione", { replace: true });
    }
  }, [user, loading, navigate]);

  const load = async () => {
    try {
      const res = await api.get("/admin/users");
      setUsers(res.data);
      setOwnerUserId((current) => current || res.data?.[0]?.user_id || "");
    } catch (e) {
      toast.error("Impossibile caricare gli utenti");
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => { if (user?.is_admin) load(); /* eslint-disable-next-line */ }, [user?.is_admin]);

  const loadCanonicalStatus = async (selectedOwnerId = ownerUserId) => {
    if (!selectedOwnerId) {
      setCanonicalStatus(null);
      return;
    }
    setCanonicalStatusBusy(true);
    try {
      const res = await api.get("/admin/canonicalization/status", {
        params: { user_id: selectedOwnerId },
      });
      setCanonicalStatus(res.data);
    } catch (e) {
      toast.error("Impossibile caricare lo stato della canonicalizzazione");
    } finally {
      setCanonicalStatusBusy(false);
    }
  };

  const loadRetryStatus = async (selectedOwnerId = ownerUserId) => {
    if (!selectedOwnerId) {
      setRetryStatus(null);
      return;
    }
    setRetryStatusBusy(true);
    try {
      const res = await api.get("/admin/translation-retry/status", {
        params: { user_id: selectedOwnerId },
      });
      setRetryStatus(res.data);
    } catch (e) {
      toast.error("Impossibile caricare lo stato del recupero traduzioni");
    } finally {
      setRetryStatusBusy(false);
    }
  };

  const loadTranslationStatus = async (selectedOwnerId = ownerUserId) => {
    if (!selectedOwnerId) {
      setTranslationStatus(null);
      return;
    }
    setTranslationStatusBusy(true);
    try {
      const res = await api.get("/admin/translation-verification/status", {
        params: { user_id: selectedOwnerId },
      });
      setTranslationStatus(res.data);
    } catch (e) {
      toast.error("Impossibile caricare lo stato delle traduzioni");
    } finally {
      setTranslationStatusBusy(false);
    }
  };

  useEffect(() => {
    if (user?.is_admin && ownerUserId) {
      loadRetryStatus();
      loadTranslationStatus();
      loadCanonicalStatus();
    }
    // The status is intentionally refreshed after an explicit batch only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ownerUserId, user?.is_admin]);

  const runTranslationRetry = async () => {
    const normalizedBatchSize = Math.max(1, Math.min(25, Number(retryBatchSize) || 1));
    setRetryBatchSize(normalizedBatchSize);
    setRetryBusy(true);
    try {
      const res = await api.post("/admin/translation-retry/run", {
        user_id: ownerUserId,
        batch_size: normalizedBatchSize,
      });
      setRetryStatus(res.data);
      await loadTranslationStatus();
      toast.success(
        res.data?.recovered_records
          ? `Recuperate ${res.data.recovered_records} traduzioni`
          : "Batch di recupero traduzioni completato",
      );
    } catch (e) {
      toast.error("Recupero delle traduzioni non riuscito");
    } finally {
      setRetryBusy(false);
    }
  };

  const runTranslationVerification = async () => {
    const normalizedBatchSize = Math.max(1, Math.min(25, Number(translationBatchSize) || 1));
    setTranslationBatchSize(normalizedBatchSize);
    setTranslationBusy(true);
    try {
      const res = await api.post("/admin/translation-verification/run", {
        user_id: ownerUserId,
        batch_size: normalizedBatchSize,
      });
      setTranslationStatus(res.data);
      toast.success("Batch di verifica traduzioni completato");
    } catch (e) {
      toast.error("Verifica delle traduzioni non riuscita");
    } finally {
      setTranslationBusy(false);
    }
  };

  const runCanonicalization = async () => {
    const normalizedBatchSize = Math.max(1, Math.min(25, Number(batchSize) || 1));
    setBatchSize(normalizedBatchSize);
    setCanonicalBusy(true);
    try {
      await api.post("/admin/canonicalization/run", {
        user_id: ownerUserId,
        batch_size: normalizedBatchSize,
        ruleset: "2014",
      });
      toast.success("Batch di canonicalizzazione completato");
      await loadCanonicalStatus();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      toast.error(detail?.message || "Canonicalizzazione non riuscita");
    } finally {
      setCanonicalBusy(false);
    }
  };

  const toggle = async (u, enabled) => {
    setUsers((prev) => prev.map((x) => (x.user_id === u.user_id ? { ...x, premium_manual: enabled, is_premium: enabled || x.is_premium } : x)));
    try {
      await api.post(`/admin/users/${u.user_id}/premium`, { enabled });
      toast.success(enabled ? `${u.name} ora è Premium` : `Premium rimosso a ${u.name}`);
      load();
    } catch (e) {
      toast.error("Aggiornamento fallito");
      load();
    }
  };

  const filtered = users.filter((u) => `${u.name} ${u.email}`.toLowerCase().includes(q.toLowerCase()));

  if (loading || !user?.is_admin) {
    return <div className="min-h-screen bg-obsidian flex items-center justify-center"><Loader2 className="w-6 h-6 text-gold animate-spin" /></div>;
  }

  return (
    <div className="min-h-screen bg-obsidian">
      <Navbar />
      <main className="max-w-5xl mx-auto px-4 sm:px-8 py-10">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-center gap-2 mb-2">
            <ShieldCheck className="w-5 h-5 text-gold" />
            <p className="font-label text-xs tracking-[0.3em] text-gold/70">CUSTODE DEL TOMO</p>
          </div>
          <h1 className="font-display text-4xl sm:text-5xl tf-gold-text">Gestione Premium</h1>
          <p className="font-body text-muted-foreground mt-2">Decidi tu chi ha accesso gratuito alla generazione AI e chi deve abbonarsi.</p>
        </motion.div>

        <div className="mt-6 max-w-sm">
          <Input data-testid="admin-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cerca utente…"
            className="bg-input border-border rounded-none font-body focus-visible:ring-gold" />
        </div>

        <div className="mt-6 border border-gold-deep/40 bg-card divide-y divide-border">
          {busy ? (
            <div className="p-8 flex justify-center"><Loader2 className="w-6 h-6 text-gold animate-spin" /></div>
          ) : filtered.length === 0 ? (
            <div className="p-8 text-center font-body text-muted-foreground">Nessun utente trovato</div>
          ) : (
            filtered.map((u) => (
              <div key={u.user_id} data-testid={`admin-user-${u.user_id}`} className="flex items-center justify-between gap-4 px-4 py-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-body text-foreground truncate">{u.name}</span>
                    {u.is_admin && <span className="font-label text-[9px] tracking-widest text-obsidian bg-gold px-1.5 py-0.5">ADMIN</span>}
                    {u.is_premium && <Crown className="w-3.5 h-3.5 text-gold" />}
                  </div>
                  <div className="font-body text-xs text-muted-foreground truncate">{u.email}</div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="font-label text-[10px] tracking-widest text-muted-foreground uppercase hidden sm:inline">
                    {u.premium_manual ? "Gratis (admin)" : u.is_premium ? "Abbonato" : "Non premium"}
                  </span>
                  <Switch
                    data-testid={`premium-switch-${u.user_id}`}
                    checked={!!u.premium_manual}
                    onCheckedChange={(v) => toggle(u, v)}
                    disabled={u.is_admin}
                    className="data-[state=checked]:bg-gold"
                  />
                </div>
              </div>
            ))
          )}
        </div>
        <p className="font-body text-[11px] text-muted-foreground mt-3">Lo switch concede l'accesso Premium gratuito. Gli abbonati Stripe restano Premium anche senza switch.</p>

        <section className="mt-14 border border-gold-deep/40 bg-card p-5 sm:p-7" aria-labelledby="canonicalization-title">
          <div className="flex items-start gap-3">
            <BookOpenCheck className="w-6 h-6 text-gold shrink-0 mt-1" />
            <div>
              <p className="font-label text-xs tracking-[0.25em] text-gold/70">BIBLIOTECA CANONICA</p>
              <h2 id="canonicalization-title" className="font-display text-3xl tf-gold-text mt-1">D&amp;D 5e · Regole 2014</h2>
              <p className="font-body text-sm text-muted-foreground mt-2">
                Recupera prima eventuali traduzioni fallite, poi verificale e infine crea i record canonici. Ogni batch parte solo su comando.
              </p>
            </div>
          </div>

          <div className="mt-6 max-w-xl">
            <label className="font-label text-[10px] tracking-widest text-muted-foreground uppercase">
              Proprietario libreria
              <select
                data-testid="canonical-owner"
                value={ownerUserId}
                onChange={(e) => {
                  setRetryStatus(null);
                  setTranslationStatus(null);
                  setCanonicalStatus(null);
                  setOwnerUserId(e.target.value);
                }}
                disabled={busy || retryBusy || translationBusy || canonicalBusy}
                className="mt-2 w-full h-10 bg-input border border-border px-3 font-body text-sm text-foreground"
              >
                {users.length === 0 && <option value="">Nessun utente disponibile</option>}
                {users.map((u) => <option key={u.user_id} value={u.user_id}>{u.name} ({u.email})</option>)}
              </select>
            </label>
          </div>

          <div className="mt-8 border border-border bg-obsidian/30 p-4 sm:p-5">
            <div className="flex items-start gap-3">
              <Languages className="w-5 h-5 text-gold shrink-0 mt-0.5" />
              <div>
                <p className="font-label text-[10px] tracking-[0.22em] text-gold/70">PREPARAZIONE</p>
                <h3 className="font-display text-2xl text-foreground">Recupero traduzioni fallite</h3>
                <p className="font-body text-xs text-muted-foreground mt-1">
                  Ritenta in piccoli batch solo le traduzioni non riuscite, senza rileggere i PDF né modificare il testo sorgente.
                </p>
              </div>
            </div>

            <div className="grid sm:grid-cols-[150px_auto] gap-4 mt-5 items-end">
              <label className="font-label text-[10px] tracking-widest text-muted-foreground uppercase">
                Record per batch
                <Input
                  data-testid="retry-batch-size"
                  type="number"
                  min="1"
                  max="25"
                  value={retryBatchSize}
                  onChange={(e) => setRetryBatchSize(e.target.value)}
                  disabled={!ownerUserId || retryBusy || !retryStatus?.retryable_total}
                  className="mt-2 bg-input border-border rounded-none font-body"
                />
              </label>
              <button
                type="button"
                data-testid="retry-run"
                onClick={runTranslationRetry}
                disabled={!ownerUserId || retryBusy || !retryStatus?.retryable_total}
                className="h-10 px-4 bg-gold text-obsidian font-label text-xs tracking-widest uppercase inline-flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {retryBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {retryBusy ? "In corso…" : "Recupera / riprendi"}
              </button>
            </div>

            {retryStatusBusy ? (
              <div className="mt-5 flex items-center gap-2 text-muted-foreground font-body text-sm"><Loader2 className="w-4 h-4 animate-spin" /> Caricamento stato…</div>
            ) : retryStatus && (
              <div data-testid="retry-status" className="mt-5">
                <div className="flex flex-wrap justify-between gap-2 font-body text-sm text-muted-foreground">
                  <span>Tradotte: {retryStatus.translated_total || 0} su {retryStatus.translatable_total || 0}</span>
                  <span className={retryStatus.ready_for_verification ? "text-emerald-400" : "text-amber-300"}>
                    {retryStatus.ready_for_verification ? "Pronte per la verifica AI" : "Recupero ancora necessario"}
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-border border border-border mt-3">
                  {[
                    ["Fallite", retryStatus.failed_total],
                    ["Ritentabili", retryStatus.retryable_total],
                    ["In corso", retryStatus.processing_total],
                    ["Bloccate", retryStatus.blocked_total],
                  ].map(([label, value]) => (
                    <div key={label} className="bg-card px-3 py-3">
                      <div className="font-label text-[9px] tracking-widest text-muted-foreground uppercase">{label}</div>
                      <div className="font-display text-2xl text-foreground mt-1">{value || 0}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="mt-5 border border-border bg-obsidian/30 p-4 sm:p-5">
            <div className="flex items-start gap-3">
              <Languages className="w-5 h-5 text-gold shrink-0 mt-0.5" />
              <div>
                <p className="font-label text-[10px] tracking-[0.22em] text-gold/70">FASE 1</p>
                <h3 className="font-display text-2xl text-foreground">Verifica AI delle traduzioni</h3>
                <p className="font-body text-xs text-muted-foreground mt-1">
                  Confronta l&apos;italiano con l&apos;originale senza modificare né certificare i casi dubbi.
                </p>
              </div>
            </div>

            <div className="grid sm:grid-cols-[150px_auto] gap-4 mt-5 items-end">
              <label className="font-label text-[10px] tracking-widest text-muted-foreground uppercase">
                Record per batch
                <Input
                  data-testid="translation-batch-size"
                  type="number"
                  min="1"
                  max="25"
                  value={translationBatchSize}
                  onChange={(e) => setTranslationBatchSize(e.target.value)}
                  disabled={!ownerUserId || translationBusy || !retryStatus?.ready_for_verification}
                  className="mt-2 bg-input border-border rounded-none font-body"
                />
              </label>
              <button
                type="button"
                data-testid="translation-run"
                onClick={runTranslationVerification}
                disabled={!ownerUserId || translationBusy || !retryStatus?.ready_for_verification}
                className="h-10 px-4 bg-gold text-obsidian font-label text-xs tracking-widest uppercase inline-flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {translationBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {translationBusy ? "In corso…" : "Verifica / riprendi"}
              </button>
            </div>

            {!retryStatus?.ready_for_verification && !retryStatusBusy && (
              <p data-testid="translation-retry-gate" className="font-body text-xs text-amber-300 mt-3">
                Completa prima il recupero delle traduzioni non pronte.
              </p>
            )}

            {translationStatusBusy ? (
              <div className="mt-5 flex items-center gap-2 text-muted-foreground font-body text-sm"><Loader2 className="w-4 h-4 animate-spin" /> Caricamento stato…</div>
            ) : translationStatus && (
              <div data-testid="translation-status" className="mt-5">
                <div className="flex flex-wrap justify-between gap-2 font-body text-sm text-muted-foreground">
                  <span>Verifica completata: {translationStatus.verification_complete || 0} su {translationStatus.translatable_total || 0}</span>
                  <span className={translationStatus.ready_for_canonicalization ? "text-emerald-400" : "text-amber-300"}>
                    {translationStatus.ready_for_canonicalization ? "Pronte per la fase 2" : "Fase 2 bloccata in sicurezza"}
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-px bg-border border border-border mt-3">
                  {[
                    ["Verificate AI", translationStatus.ai_verified],
                    ["Da verificare", translationStatus.pending],
                    ["Conflitti", translationStatus.conflict],
                    ["Bassa confidenza", translationStatus.low_confidence],
                    ["Traduzioni fallite", translationStatus.translation_failed],
                    ["Verifiche da ritentare", translationStatus.failed],
                  ].map(([label, value]) => (
                    <div key={label} className="bg-card px-3 py-3">
                      <div className="font-label text-[9px] tracking-widest text-muted-foreground uppercase">{label}</div>
                      <div className="font-display text-2xl text-foreground mt-1">{value || 0}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="mt-5 border border-border bg-obsidian/30 p-4 sm:p-5">
            <div>
              <p className="font-label text-[10px] tracking-[0.22em] text-gold/70">FASE 2</p>
              <h3 className="font-display text-2xl text-foreground">Canonicalizzazione delle fonti</h3>
              <p className="font-body text-xs text-muted-foreground mt-1">
                Seleziona un record completo senza fondere testi di manuali diversi e conserva tutta la provenienza.
              </p>
            </div>

            <div className="grid sm:grid-cols-[150px_auto] gap-4 mt-5 items-end">
              <label className="font-label text-[10px] tracking-widest text-muted-foreground uppercase">
                Gruppi per batch
                <Input
                  data-testid="canonical-batch-size"
                  type="number"
                  min="1"
                  max="25"
                  value={batchSize}
                  onChange={(e) => setBatchSize(e.target.value)}
                  disabled={!ownerUserId || canonicalBusy}
                  className="mt-2 bg-input border-border rounded-none font-body"
                />
              </label>
              <button
                type="button"
                data-testid="canonical-run"
                onClick={runCanonicalization}
                disabled={!ownerUserId || canonicalBusy || !translationStatus?.ready_for_canonicalization}
                className="h-10 px-4 bg-gold text-obsidian font-label text-xs tracking-widest uppercase inline-flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {canonicalBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {canonicalBusy ? "In corso…" : "Avvia / riprendi"}
              </button>
            </div>

            {!translationStatus?.ready_for_canonicalization && !translationStatusBusy && (
              <p data-testid="canonical-translation-gate" className="font-body text-xs text-amber-300 mt-3">
                Completa la fase 1 e risolvi le traduzioni non pronte prima di avviare la canonicalizzazione.
              </p>
            )}

            {canonicalStatusBusy ? (
              <div className="mt-5 flex items-center gap-2 text-muted-foreground font-body text-sm"><Loader2 className="w-4 h-4 animate-spin" /> Caricamento stato…</div>
            ) : canonicalStatus && (
              <div data-testid="canonical-status" className="mt-5">
                <div className="flex justify-between gap-4 font-body text-sm text-muted-foreground">
                  <span>Progresso: {canonicalStatus.canonical_total || 0} canonici su {canonicalStatus.records_total || 0} record</span>
                  <span>{canonicalStatus.ruleset || "2014"}</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-px bg-border border border-border mt-3">
                  {[
                    ["Verificati", canonicalStatus.verified_groups],
                    ["Conflitti", canonicalStatus.conflict_groups],
                    ["Bassa confidenza", canonicalStatus.low_confidence_groups],
                    ["In attesa", canonicalStatus.pending_groups],
                    ["Esclusi", canonicalStatus.excluded_records],
                  ].map(([label, value]) => (
                    <div key={label} className="bg-card px-3 py-3">
                      <div className="font-label text-[9px] tracking-widest text-muted-foreground uppercase">{label}</div>
                      <div className="font-display text-2xl text-foreground mt-1">{value || 0}</div>
                    </div>
                  ))}
                </div>
                <p className="font-body text-xs text-muted-foreground mt-3">
                  I gruppi con conflitti o bassa confidenza restano bloccati come dati incerti. Una successiva esecuzione può
                  rivalutarli quando cambiano le fonti, senza imporre una revisione manuale record per record.
                </p>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
