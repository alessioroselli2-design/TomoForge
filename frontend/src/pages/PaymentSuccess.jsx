import React, { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Crown, Loader2, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function PaymentSuccess() {
  const navigate = useNavigate();
  const { checkAuth } = useAuth();
  const [status, setStatus] = useState("checking");
  const attempts = useRef(0);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get("session_id");
    if (!sessionId) { setStatus("error"); return; }

    let timer;
    const poll = async () => {
      attempts.current += 1;
      try {
        const res = await api.get(`/payments/status/${sessionId}`);
        if (res.data.payment_status === "paid") {
          await checkAuth();
          setStatus("done");
          setTimeout(() => navigate("/crea", { replace: true }), 2200);
          return;
        }
      } catch (e) { /* keep polling */ }
      if (attempts.current >= 15) { setStatus("timeout"); return; }
      timer = setTimeout(poll, 2000);
    };
    poll();
    return () => clearTimeout(timer);
  }, [checkAuth, navigate]);

  return (
    <div className="min-h-screen bg-obsidian tf-noise flex flex-col items-center justify-center px-6 text-center">
      {status === "done" ? (
        <>
          <CheckCircle2 className="w-14 h-14 text-gold mb-5" data-testid="payment-success-icon" />
          <h1 className="font-display text-4xl tf-gold-text">Premium Attivato!</h1>
          <p className="font-body text-foreground/75 mt-3 max-w-md">Il potere dell'arcano è tuo. Ti sto portando alla forgia delle carte…</p>
        </>
      ) : status === "timeout" ? (
        <>
          <Crown className="w-12 h-12 text-gold/60 mb-5" />
          <h1 className="font-heading text-3xl text-foreground">Pagamento in elaborazione</h1>
          <p className="font-body text-muted-foreground mt-3 max-w-md">Il pagamento sta venendo confermato. Aggiorna tra poco o controlla la tua collezione.</p>
          <button onClick={() => navigate("/collezione")} className="mt-6 font-label text-xs tracking-widest text-gold border border-gold-deep/50 px-5 py-2.5 hover:bg-secondary transition-colors">VAI ALLA COLLEZIONE</button>
        </>
      ) : status === "error" ? (
        <>
          <h1 className="font-heading text-3xl text-foreground">Sessione non valida</h1>
          <button onClick={() => navigate("/collezione")} className="mt-6 font-label text-xs tracking-widest text-gold border border-gold-deep/50 px-5 py-2.5 hover:bg-secondary transition-colors">TORNA INDIETRO</button>
        </>
      ) : (
        <>
          <Loader2 className="w-10 h-10 text-gold animate-spin mb-5" />
          <p className="font-label text-gold tracking-widest animate-pulse">CONFERMA DEL PAGAMENTO…</p>
        </>
      )}
    </div>
  );
}
