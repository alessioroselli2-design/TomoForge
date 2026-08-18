import React from "react";
import { useNavigate } from "react-router-dom";
import { XCircle } from "lucide-react";

export default function PaymentCancel() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-obsidian tf-noise flex flex-col items-center justify-center px-6 text-center">
      <XCircle className="w-12 h-12 text-crimson/70 mb-5" />
      <h1 className="font-heading text-3xl text-foreground">Pagamento annullato</h1>
      <p className="font-body text-muted-foreground mt-3 max-w-md">Nessun addebito effettuato. Puoi abbonarti quando vuoi per sbloccare la generazione AI.</p>
      <button data-testid="cancel-back-btn" onClick={() => navigate("/collezione")} className="mt-6 font-label text-xs tracking-widest text-gold border border-gold-deep/50 px-5 py-2.5 hover:bg-secondary transition-colors">TORNA ALLA COLLEZIONE</button>
    </div>
  );
}
