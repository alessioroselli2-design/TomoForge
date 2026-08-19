import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";

const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const res = await api.get("/auth/me");
      setUser(res.data);
    } catch (e) {
      setUser(null);
    } finally {
      setLoading(false);
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

  const loginWithToken = (token, userData) => {
    if (token) localStorage.setItem("tf_token", token);
    setUser(userData);
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch (e) {}
    localStorage.removeItem("tf_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, loading, checkAuth, loginWithToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
