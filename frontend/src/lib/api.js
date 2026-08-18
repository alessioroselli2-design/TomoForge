import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
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
