import "@/App.css";
import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Landing from "@/pages/Landing";

















import { LanguageProvider } from "@/lib/i18n";
import { api } from "@/lib/api";
import { isTemporaryAuthError } from "@/lib/authRead";
import EditorErrorBoundary from "@/components/EditorErrorBoundary";
const Collection=React.lazy(()=>import("@/pages/Collection"));
const CardEditor=React.lazy(()=>import("@/pages/CardEditor"));
const CardDetail=React.lazy(()=>import("@/pages/CardDetail"));
const CharacterSheet=React.lazy(()=>import("@/pages/CharacterSheet"));
const PublicCard=React.lazy(()=>import("@/pages/PublicCard"));
const PublicDescription=React.lazy(()=>import("@/pages/PublicDescription"));
const PaymentSuccess=React.lazy(()=>import("@/pages/PaymentSuccess"));
const PaymentCancel=React.lazy(()=>import("@/pages/PaymentCancel"));
const Admin=React.lazy(()=>import("@/pages/Admin"));
const ReferenceReview=React.lazy(()=>import("@/pages/ReferenceReview"));
const DiceMasterPreview=React.lazy(()=>import("@/pages/DiceMasterPreview"));
const ClassAbilityPreview=React.lazy(()=>import("@/pages/ClassAbilityPreview"));
const SpellCardPreview=React.lazy(()=>import("@/pages/SpellCardPreview"));
const FeatureCardPreview=React.lazy(()=>import("@/pages/FeatureCardPreview"));
const RaceCardPreview=React.lazy(()=>import("@/pages/RaceCardPreview"));
const CategoryCardPreview=React.lazy(()=>import("@/pages/CategoryCardPreview"));
const PrintPressPreview=React.lazy(()=>import("@/pages/PrintPressPreview"));

const Protected = ({ children }) => {
  const { user, loading, authError, checkAuth } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-obsidian">
        <p className="font-label text-gold tracking-widest animate-pulse">APERTURA DEL TOMO…</p>
      </div>
    );
  }
  if (authError&&!user)return <div className="min-h-screen flex flex-col gap-4 items-center justify-center bg-obsidian px-6 text-center">
    <p className="text-gold">Connessione temporaneamente non disponibile.</p>
    <button type="button" onClick={checkAuth} className="border border-gold px-4 py-2 text-gold">RIPROVA</button>
  </div>;
  if (!user) return <Navigate to="/" replace />;
  return children;
};

function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/oauth/callback" element={<OAuthCallback />} />
      <Route path="/p/:id" element={<PublicCard />} />
      <Route path="/d/:id" element={<PublicDescription />} />
      <Route path="/prova-dadi-v29" element={<DiceMasterPreview />} />
      <Route path="/prova-classi" element={<ClassAbilityPreview />} />
      <Route path="/prova-incantesimi" element={<SpellCardPreview />} />
      <Route path="/prova-privilegi" element={<FeatureCardPreview />} />
      <Route path="/prova-razze" element={<RaceCardPreview />} />
      <Route path="/prova-categorie" element={<CategoryCardPreview />} />
      <Route path="/prova-stampa" element={<PrintPressPreview />} />
      <Route path="/collezione" element={<Protected><Collection /></Protected>} />
      <Route path="/crea" element={<Protected><EditorErrorBoundary><CardEditor /></EditorErrorBoundary></Protected>} />
      <Route path="/revisioni" element={<Protected><ReferenceReview /></Protected>} />
      <Route path="/carta/:id/modifica" element={<Protected><EditorErrorBoundary><CardEditor /></EditorErrorBoundary></Protected>} />
      <Route path="/carta/:id/scheda" element={<Protected><CharacterSheet /></Protected>} />
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
  const [error, setError] = React.useState("");
  const [retryable,setRetryable]=React.useState(false);
  const exchange=React.useRef(null);
  const tokenRef=React.useRef(null);
  const [attempt,setAttempt]=React.useState(0);

  React.useEffect(() => {
    let active=true;
    if (!tokenRef.current) {
      const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
      const queryParams = new URLSearchParams(window.location.search);
      const accessToken = hashParams.get("access_token");
      const providerError = hashParams.get("error_description") || queryParams.get("error_description") || hashParams.get("error") || queryParams.get("error");
      window.history.replaceState(null, "", "/oauth/callback");
      if (!accessToken) {
        setError(providerError || "Google non ha restituito una sessione valida. Riprova l'accesso.");
        return;
      }
      tokenRef.current=accessToken;
    }
    if(!exchange.current)exchange.current=api.post("/auth/supabase-session",{access_token:tokenRef.current},{timeout:20000});
    exchange.current.then(({data})=>{
      if(!active)return;
      tokenRef.current=null;
      loginWithToken(data.token,data.user);
      navigate("/collezione",{replace:true});
    }).catch(requestError=>{
      if(!active)return;
      exchange.current=null;
      const temporary=isTemporaryAuthError(requestError);
      setRetryable(temporary);
      setError(temporary?"Connessione temporaneamente non disponibile. Puoi riprovare senza tornare al login.":(requestError.response?.data?.detail||"Impossibile completare l'accesso Google. Riprova."));
    });
    return()=>{active=false;};
  }, [loginWithToken, navigate, attempt]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-obsidian">
      <div className="max-w-md px-6 text-center">
        <p className={`font-label text-gold tracking-widest ${error ? "" : "animate-pulse"}`}>
          {error ? "ACCESSO GOOGLE NON COMPLETATO" : "APERTURA DEL TOMO…"}
        </p>
        {error && (
          <>
            <p className="mt-4 font-body text-sm leading-relaxed text-foreground/75">{error}</p>
            {retryable&&<button type="button" onClick={()=>{setError("");setRetryable(false);setAttempt(n=>n+1);}} className="mt-6 block mx-auto border border-gold px-4 py-2 text-gold">RIPROVA CONNESSIONE</button>}
            <button
              type="button"
              onClick={() => navigate("/", { replace: true })}
              className="mt-6 font-label text-xs tracking-widest text-gold hover:text-gold-deep"
            >
              TORNA AL LOGIN
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function App() {
  return (
    <div className="App tf-noise">
      {window.location.hostname.endsWith("-alessio-roselli-s-projects.vercel.app")&&<div data-testid="preview-build" className="bg-amber-950 text-amber-100 text-center text-xs px-2 py-1">ANTEPRIMA TEST · STABILITÀ 705</div>}
      <BrowserRouter>
        <AuthProvider>
          <LanguageProvider>
            <Toaster position="top-center" theme="dark" toastOptions={{ style: { background: "#151311", border: "1px solid #9a7d2e", color: "#e5e0d8", fontFamily: "'Spectral', serif" } }} />
            <React.Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-obsidian"><p className="font-label text-gold animate-pulse">APERTURA DEL TOMO…</p></div>}><AppRouter /></React.Suspense>
          </LanguageProvider>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
