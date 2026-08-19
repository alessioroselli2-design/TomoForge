import "@/App.css";
import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Landing from "@/pages/Landing";
import Collection from "@/pages/Collection";
import CardEditor from "@/pages/CardEditor";
import CardDetail from "@/pages/CardDetail";
import PublicCard from "@/pages/PublicCard";
import PaymentSuccess from "@/pages/PaymentSuccess";
import PaymentCancel from "@/pages/PaymentCancel";
import Admin from "@/pages/Admin";
import { LanguageProvider } from "@/lib/i18n";
import { api } from "@/lib/api";

const Protected = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-obsidian">
        <p className="font-label text-gold tracking-widest animate-pulse">APERTURA DEL TOMO…</p>
      </div>
    );
  }
  if (!user) return <Navigate to="/" replace />;
  return children;
};

function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/oauth/callback" element={<OAuthCallback />} />
      <Route path="/p/:id" element={<PublicCard />} />
      <Route path="/collezione" element={<Protected><Collection /></Protected>} />
      <Route path="/crea" element={<Protected><CardEditor /></Protected>} />
      <Route path="/carta/:id/modifica" element={<Protected><CardEditor /></Protected>} />
      <Route path="/carta/:id" element={<Protected><CardDetail /></Protected>} />
      <Route path="/payment/success" element={<Protected><PaymentSuccess /></Protected>} />
      <Route path="/payment/cancel" element={<Protected><PaymentCancel /></Protected>} />
      <Route path="/admin" element={<Protected><Admin /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function OAuthCallback() {
  const navigate = useNavigate();
  const { loginWithToken } = useAuth();

  React.useEffect(() => {
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const accessToken = params.get("access_token");
    window.history.replaceState(null, "", "/oauth/callback");
    if (!accessToken) {
      navigate("/", { replace: true });
      return;
    }
    api.post("/auth/supabase-session", { access_token: accessToken })
      .then(({ data }) => {
        loginWithToken(data.token, data.user);
        navigate("/collezione", { replace: true });
      })
      .catch(() => navigate("/", { replace: true }));
  }, [loginWithToken, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-obsidian">
      <p className="font-label text-gold tracking-widest animate-pulse">APERTURA DEL TOMO…</p>
    </div>
  );
}

function App() {
  return (
    <div className="App tf-noise">
      <BrowserRouter>
        <AuthProvider>
          <LanguageProvider>
            <Toaster position="top-center" theme="dark" toastOptions={{ style: { background: "#151311", border: "1px solid #9a7d2e", color: "#e5e0d8", fontFamily: "'Spectral', serif" } }} />
            <AppRouter />
          </LanguageProvider>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
