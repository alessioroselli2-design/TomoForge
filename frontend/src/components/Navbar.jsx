import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { BookOpen, LogOut, Plus, Crown, ShieldCheck } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { PremiumDialog } from "@/components/PremiumDialog";
import { useI18n } from "@/lib/i18n";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [premiumOpen, setPremiumOpen] = useState(false);
  const { t } = useI18n();

  const doLogout = async () => {
    await logout();
    navigate("/", { replace: true });
  };

  const initials = (user?.name || "?").slice(0, 1).toUpperCase();

  return (
    <header className="sticky top-0 z-40 border-b border-gold-deep/30 bg-obsidian/90 backdrop-blur-sm">
      <PremiumDialog open={premiumOpen} onOpenChange={setPremiumOpen} />
      <div className="max-w-7xl mx-auto px-4 sm:px-8 h-16 flex items-center justify-between">
        <Link to="/collezione" data-testid="nav-logo" className="flex shrink-0 items-center gap-2 sm:gap-3 group">
          <BookOpen className="w-6 h-6 text-gold transition-transform group-hover:-translate-y-0.5" strokeWidth={1.5} />
          <span className="hidden font-label tracking-[0.3em] text-gold text-sm min-[390px]:block">TOMEFORGE</span>
        </Link>

        <div className="flex items-center gap-3">
          {user && !user.is_premium && (
            <Button data-testid="nav-upgrade" onClick={() => setPremiumOpen(true)} variant="outline"
              className="hidden rounded-none border-gold-deep/50 bg-transparent text-gold hover:bg-secondary font-label tracking-wide text-xs h-9 px-3 transition-colors md:inline-flex">
              <Crown className="w-4 h-4 mr-1.5" /> PREMIUM
            </Button>
          )}
          {user?.is_premium && (
            <span data-testid="nav-premium-badge" className="hidden sm:flex items-center gap-1.5 border border-gold/60 px-2.5 h-9 font-label text-[10px] tracking-widest text-gold">
              <Crown className="w-3.5 h-3.5" /> PREMIUM
            </span>
          )}
          <Button data-testid="nav-create" onClick={() => navigate("/crea")}
            aria-label={t("create")}
            className="rounded-none bg-gold text-obsidian hover:bg-gold-deep font-label tracking-wide text-xs h-9 px-3 sm:px-4 transition-colors">
            <Plus className="w-4 h-4 sm:mr-1.5" /> <span className="hidden sm:inline">{t("create").toUpperCase()}</span>
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger data-testid="nav-user" className="outline-none">
              {user?.picture ? (
                <img src={user.picture} alt="avatar" className="w-9 h-9 rounded-full border border-gold-deep object-cover" />
              ) : (
                <div className="w-9 h-9 rounded-full border border-gold-deep bg-secondary flex items-center justify-center font-label text-gold text-sm">
                  {initials}
                </div>
              )}
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="bg-card border-gold-deep/40 rounded-none">
              <div className="px-3 py-2 border-b border-border">
                <p className="font-body text-sm text-foreground truncate">{user?.name}</p>
                <p className="font-body text-xs text-muted-foreground truncate">{user?.email}</p>
              </div>
              {user?.is_admin && (
                <DropdownMenuItem data-testid="nav-admin" onClick={() => navigate("/admin")}
                  className="font-label text-xs tracking-wide cursor-pointer focus:bg-secondary focus:text-gold">
                  <ShieldCheck className="w-4 h-4 mr-2" /> PANNELLO ADMIN
                </DropdownMenuItem>
              )}
              <DropdownMenuItem data-testid="nav-logout" onClick={doLogout}
                className="font-label text-xs tracking-wide cursor-pointer focus:bg-secondary focus:text-crimson">
                <LogOut className="w-4 h-4 mr-2" /> ESCI DAL TOMO
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
