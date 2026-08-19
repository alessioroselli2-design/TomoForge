import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

// UI dictionaries are intentionally separate from card content. Card content keeps
// its own language field, so changing the interface language never rewrites user data.
const dictionaries = {
  it: {
    collection: "La Collezione", create: "Nuova carta", printSheet: "Foglio di stampa",
    selectAll: "Seleziona tutte", deselectAll: "Deseleziona", exportPdf: "Esporta PDF",
    format: "Formato", includeBack: "Includi retro (F/R)", completeDetails: "Dettagli completi",
    front: "Mostra fronte", back: "Mostra retro", language: "Lingua interfaccia",
    foil: "Cornice foil", gold: "Oro", silver: "Argento", rainbow: "Arcobaleno",
    none: "Nessuna", edit: "Modifica", image: "Immagine", save: "Salva modifiche",
  },
  en: {
    collection: "Collection", create: "New card", printSheet: "Print sheet",
    selectAll: "Select all", deselectAll: "Deselect", exportPdf: "Export PDF",
    format: "Format", includeBack: "Include back (D/S)", completeDetails: "Full details",
    front: "Show front", back: "Show back", language: "Interface language",
    foil: "Foil frame", gold: "Gold", silver: "Silver", rainbow: "Rainbow",
    none: "None", edit: "Edit", image: "Image", save: "Save changes",
  },
  es: {
    collection: "Colección", create: "Nueva carta", printSheet: "Hoja de impresión",
    selectAll: "Seleccionar todas", deselectAll: "Deseleccionar", exportPdf: "Exportar PDF",
    format: "Formato", includeBack: "Incluir reverso (A/R)", completeDetails: "Detalles completos",
    front: "Mostrar frente", back: "Mostrar reverso", language: "Idioma de la interfaz",
    foil: "Marco foil", gold: "Oro", silver: "Plata", rainbow: "Arcoíris",
    none: "Ninguno", edit: "Editar", image: "Imagen", save: "Guardar cambios",
  },
  de: {
    collection: "Sammlung", create: "Neue Karte", printSheet: "Druckbogen",
    selectAll: "Alle auswählen", deselectAll: "Auswahl aufheben", exportPdf: "PDF exportieren",
    format: "Format", includeBack: "Rückseite einschließen (V/R)", completeDetails: "Vollständige Details",
    front: "Vorderseite zeigen", back: "Rückseite zeigen", language: "Sprache der Oberfläche",
    foil: "Folienrahmen", gold: "Gold", silver: "Silber", rainbow: "Regenbogen",
    none: "Keine", edit: "Bearbeiten", image: "Bild", save: "Änderungen speichern",
  },
};

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [locale, setLocale] = useState(() => localStorage.getItem("tf_locale") || "it");
  useEffect(() => { localStorage.setItem("tf_locale", locale); document.documentElement.lang = locale; }, [locale]);
  const value = useMemo(() => ({
    locale,
    setLocale,
    languages: [
      ["it", "Italiano"], ["en", "English"], ["es", "Español"], ["de", "Deutsch"],
    ],
    t: (key) => dictionaries[locale]?.[key] || dictionaries.it[key] || key,
  }), [locale]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export const useI18n = () => {
  const context = useContext(LanguageContext);
  if (!context) throw new Error("useI18n must be used inside LanguageProvider");
  return context;
};