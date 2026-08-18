import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Crown, ShieldCheck, Loader2 } from "lucide-react";
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

  useEffect(() => {
    if (!loading && (!user || !user.is_admin)) {
      navigate("/collezione", { replace: true });
    }
  }, [user, loading, navigate]);

  const load = async () => {
    try {
      const res = await api.get("/admin/users");
      setUsers(res.data);
    } catch (e) {
      toast.error("Impossibile caricare gli utenti");
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => { if (user?.is_admin) load(); /* eslint-disable-next-line */ }, [user]);

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
      </main>
    </div>
  );
}
