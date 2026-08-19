import axios from "axios";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");
// Empty URL intentionally means same-origin `/api`, which CRA proxies to FastAPI in development
// and keeps deployed requests on the same site.
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API, withCredentials: true });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("tf_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Build an authenticated image URL for <img src>
export const artworkUrl = (path) => {
  if (!path) return null;
  const token = localStorage.getItem("tf_token") || "";
  return `${API}/files/${path}?auth=${encodeURIComponent(token)}`;
};

// Public (no auth) image URL, used by shareable card view
export const publicArtworkUrl = (path) => (path ? `${API}/public/files/${path}` : null);
