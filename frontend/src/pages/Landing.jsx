import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { BookOpen, Sparkles } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const HERO = "https://images.unsplash.com/photo-1774366127010-9835ae1373a0?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTB8MHwxfHNlYXJjaHwzfHxhbmNpZW50JTIwc3BlbGxib29rJTIwZ3JpbW9pcmUlMjBkYXJrfGVufDB8fHx8MTc4NzAzMjcyOXww&ixlib=rb-4.1.0&q=85";

export default function Landing() {
  const navigate = useNavigate();
  const { user, loading, loginWithToken } = useAuth();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [busy, setBusy] = useState(false);

  React.useEffect(() => {
    if (!loading && user) navigate("/collezione", { replace: true });
  }, [user, loading, navigate]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const endpoint = mode === "login" ? "/auth/login" : "/auth/register";
      const payload = mode === "login"
        ? { email: form.email, password: form.password }
        : { name: form.name, email: form.email, password: form.password };
      const res = await api.post(endpoint, payload);
      loginWithToken(res.data.token, res.data.user);
      toast.success(mode === "login" ? "Bentornato, evocatore." : "Il tuo tomo è stato forgiato.");
      navigate("/collezione", { replace: true });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Qualcosa è andato storto");
    } finally {
      setBusy(false);
    }
  };

  const googleLogin = async () => {
    try {
      const res = await api.get("/auth/google/start", {
        params: { redirect_to: `${window.location.origin}/oauth/callback` },
      });
      window.location.assign(res.data.url);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Accesso Google non disponibile");
    }
  };

  return (
    <div className="min-h-screen w-full relative flex flex-col lg:flex-row">
      {/* Left: hero */}
      <div className="relative lg:w-[55%] min-h-[38vh] lg:min-h-screen overflow-hidden">
        <img src={HERO} alt="Antico tomo" className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-b from-obsidian/50 via-obsidian/70 to-obsidian" />
        <div className="absolute inset-0 bg-obsidian/40" />
        <motion.div
          initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9 }}
          className="relative z-10 h-full flex flex-col justify-end lg:justify-center px-8 sm:px-14 py-12"
        >
          <div className="flex items-center gap-3 mb-6">
            <BookOpen className="w-7 h-7 text-gold" strokeWidth={1.5} />
            <span className="font-label tracking-[0.35em] text-gold text-sm">TOMEFORGE</span>
          </div>
          <h1 className="font-display text-5xl sm:text-6xl lg:text-7xl leading-[0.95] tf-gold-text max-w-2xl">
            Forgia le tue<br />leggende di D&amp;D
          </h1>
          <p className="font-body text-base sm:text-lg text-foreground/75 mt-6 max-w-xl">
            Crea magie, mostri, personaggi e artefatti come autentiche carte da collezione.
            Contenuti e artwork evocati dall'arcano, incisi nel tuo grimorio personale.
          </p>
          <div className="flex flex-wrap gap-x-8 gap-y-2 mt-8 font-label text-xs tracking-widest text-gold/70">
            <span>· GENERAZIONE AI</span>
            <span>· ARTWORK FANTASY</span>
            <span>· STAT BLOCK 5e</span>
            <span>· STAMPA PDF</span>
          </div>
        </motion.div>
      </div>

      {/* Right: auth */}
      <div className="lg:w-[45%] flex items-center justify-center px-6 sm:px-12 py-14 bg-obsidian relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.2 }}
          className="w-full max-w-md border border-gold-deep/40 bg-card p-8 sm:p-10 shadow-2xl shadow-black/60"
        >
          <div className="flex mb-8 border-b border-border">
            {["login", "register"].map((m) => (
              <button
                key={m}
                data-testid={`tab-${m}`}
                onClick={() => setMode(m)}
                className={`flex-1 pb-3 font-label text-sm tracking-widest transition-colors ${mode === m ? "text-gold border-b-2 border-gold" : "text-muted-foreground hover:text-foreground"}`}
              >
                {m === "login" ? "ACCEDI" : "REGISTRATI"}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-5">
            {mode === "register" && (
              <div>
                <Label className="font-label text-xs tracking-widest text-gold/80">NOME EVOCATORE</Label>
                <Input data-testid="name-input" autoComplete="name" required value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="mt-2 bg-input border-border rounded-none font-body focus-visible:ring-gold" placeholder="Il tuo nome" />
              </div>
            )}
            <div>
              <Label className="font-label text-xs tracking-widest text-gold/80">EMAIL</Label>
              <Input data-testid="email-input" type="email" autoComplete="email" required value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="mt-2 bg-input border-border rounded-none font-body focus-visible:ring-gold" placeholder="tu@grimorio.it" />
            </div>
            <div>
              <Label className="font-label text-xs tracking-widest text-gold/80">PAROLA D'ORDINE</Label>
              <Input data-testid="password-input" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="mt-2 bg-input border-border rounded-none font-body focus-visible:ring-gold" placeholder="••••••••" />
            </div>

            <Button data-testid="submit-auth" type="submit" disabled={busy}
              className="w-full rounded-none bg-gold text-obsidian hover:bg-gold-deep font-label tracking-widest h-11 transition-colors">
              {busy ? "…" : mode === "login" ? "ENTRA NEL TOMO" : "FORGIA IL TOMO"}
            </Button>
          </form>

          <div className="flex items-center gap-4 my-6">
            <div className="h-px flex-1 bg-border" />
            <span className="font-label text-[10px] tracking-widest text-muted-foreground">OPPURE</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <Button data-testid="google-login" onClick={googleLogin} variant="outline"
            className="w-full rounded-none border-gold-deep/50 bg-transparent text-foreground hover:bg-secondary hover:text-gold font-label tracking-wide h-11 transition-colors">
            <Sparkles className="w-4 h-4 mr-2 text-gold" /> Continua con Google
          </Button>

        </motion.div>
      </div>
    </div>
  );
}
