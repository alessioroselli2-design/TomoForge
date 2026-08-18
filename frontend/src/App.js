import "@/App.css";
import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import Landing from "@/pages/Landing";
import Collection from "@/pages/Collection";
import CardEditor from "@/pages/CardEditor";
import CardDetail from "@/pages/CardDetail";
import PublicCard from "@/pages/PublicCard";
import PaymentSuccess from "@/pages/PaymentSuccess";
import PaymentCancel from "@/pages/PaymentCancel";
import Admin from "@/pages/Admin";

const AuthCallback = () => {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const processed = React.useRef(false);

  React.useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    const hash = window.location.hash;
    const match = hash.match(/session_id=([^&]+)/);
    const sessionId = match ? match[1] : null;
    // Clean the hash
    window.history.replaceState(null, "", window.location.pathname);
    if (!sessionId) { navigate("/"); return; }
    (async () => {
      try {
        // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
        const res = await api.post("/auth/google-session", {}, { headers: { "X-Session-ID": sessionId } });
        if (res.data.session_token) localStorage.setItem("tf_token", res.data.session_token);
        setUser(res.data.user);
        navigate("/collezione", { replace: true });
      } catch (e) {
        navigate("/");
      }
    })();
  }, [navigate, setUser]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-obsidian">
      <p className="font-label text-gold tracking-widest animate-pulse">EVOCAZIONE IN CORSO…</p>
    </div>
  );
};

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
  const location = useLocation();
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
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

function App() {
  return (
    <div className="App tf-noise">
      <BrowserRouter>
        <AuthProvider>
          <Toaster position="top-center" theme="dark" toastOptions={{ style: { background: "#151311", border: "1px solid #9a7d2e", color: "#e5e0d8", fontFamily: "'Spectral', serif" } }} />
          <AppRouter />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
