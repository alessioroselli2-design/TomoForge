import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { readAuth, isTemporaryAuthError } from "@/lib/authRead";

const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState(false);
  const generation = React.useRef(0);

  const checkAuth = useCallback(async () => {
    const current=++generation.current;
    setLoading(true);
    setAuthError(false);
    const token = localStorage.getItem("tf_token");
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const res = await readAuth(api,"/auth/me");
      if(current===generation.current)setUser(res.data);
    } catch (e) {
      if(current!==generation.current)return;
      if(isTemporaryAuthError(e))setAuthError(true);
      else {
        setUser(null);
        if(e.response?.status===401&&localStorage.getItem("tf_token")===token)localStorage.removeItem("tf_token");
      }
    } finally {
      if(current===generation.current)setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Let the OAuth callback exchange the short-lived Supabase token first.
    if (window.location.pathname === "/oauth/callback") {
      setLoading(false);
      return;
    }
    checkAuth();
  }, [checkAuth]);

  const loginWithToken = useCallback((token, userData) => {
    ++generation.current;
    if (token) localStorage.setItem("tf_token", token);
    setUser(userData);
    setAuthError(false);
    setLoading(false);
  }, []);

  const logout = async () => {
    ++generation.current;
    try { await api.post("/auth/logout",{}, {timeout:12000}); } catch (e) {}
    localStorage.removeItem("tf_token");
    setUser(null);
    setAuthError(false);
    setLoading(false);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, loading, authError, checkAuth, loginWithToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
