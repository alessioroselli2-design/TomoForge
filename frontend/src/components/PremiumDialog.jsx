import React, { useState } from "react";
import { Crown, Check, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

const PERKS = [
  "Generazione AI dei contenuti (nome, descrizione, statistiche, storia)",
  "Generazione AI dell'artwork fantasy con OpenAI",
  "Lingua italiana e inglese",
  "Tutte le altre funzioni restano incluse",
];

export const PremiumDialog = ({ open, onOpenChange }) => {
  const [loading, setLoading] = useState(false);

  const upgrade = async () => {
    setLoading(true);
    try {
      const res = await api.post("/payments/checkout", {
        lookup_key: "premium_monthly",
        origin_url: window.location.origin,
      });
      window.location.href = res.data.checkout_url;
    } catch (e) {
      toast.error("Impossibile avviare il pagamento");
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-card border-gold-deep/50 rounded-none max-w-md" data-testid="premium-dialog">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-1">
            <Crown className="w-5 h-5 text-gold" />
            <span className="font-label text-xs tracking-widest text-gold">TOMEFORGE PREMIUM</span>
          </div>
          <DialogTitle className="font-display text-3xl tf-gold-text text-left">Sblocca l'Evocazione Arcana</DialogTitle>
          <DialogDescription className="font-body text-muted-foreground text-left">
            La generazione AI di testi e immagini è una funzione Premium.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 my-2">
          {PERKS.map((p, i) => (
            <div key={i} className="flex items-start gap-2.5">
              <Check className="w-4 h-4 text-gold mt-0.5 shrink-0" />
              <span className="font-body text-sm text-foreground/85">{p}</span>
            </div>
          ))}
        </div>

        <div className="flex items-baseline gap-2 border-t border-border pt-4">
          <span className="font-display text-4xl tf-gold-text">€5</span>
          <span className="font-body text-muted-foreground">/ mese</span>
        </div>

        <Button data-testid="premium-upgrade-btn" onClick={upgrade} disabled={loading}
          className="w-full rounded-none bg-gold text-obsidian hover:bg-gold-deep font-label tracking-widest h-12 mt-2 transition-colors">
          {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Crown className="w-4 h-4 mr-2" />}
          ABBONATI ORA
        </Button>
        <p className="font-body text-[11px] text-muted-foreground text-center">
          Pagamento sicuro con Stripe · Carta di test 4242 4242 4242 4242
        </p>
      </DialogContent>
    </Dialog>
  );
};
