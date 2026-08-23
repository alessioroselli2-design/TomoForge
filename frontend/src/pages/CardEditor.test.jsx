import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { api } from "@/lib/api";
import CardEditor from "./CardEditor";

global.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
  },
}));

jest.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ user: { is_premium: true } }),
}));

jest.mock("@/components/Navbar", () => () => <nav />);
jest.mock("@/components/LibraryCoverageReadiness", () => () => null);
jest.mock("@/components/PremiumDialog", () => ({
  PremiumDialog: ({ open }) => (open ? <div /> : null),
}));
jest.mock("@/components/CardAppearanceControls", () => ({
  CardAppearanceControls: () => <div />,
}));
jest.mock("@/components/ReferenceUpdatesPanel", () => ({
  ReferenceUpdatesPanel: () => <div />,
}));
jest.mock("@/components/AttributeEditor", () => ({
  __esModule: true,
  default: () => <div />,
}));
jest.mock("@/components/TradingCard", () => ({
  CardFront: () => <div />,
  CardBack: () => <div />,
}));

jest.mock("framer-motion", () => ({
  motion: {
    div: ({ children, animate, initial, layout, transition, ...props }) => <div {...props}>{children}</div>,
  },
}));

jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn(), warning: jest.fn() },
}));

jest.mock("@/components/ui/button", () => ({
  Button: ({ children, ...props }) => <button {...props}>{children}</button>,
}));

jest.mock("@/components/ui/input", () => ({
  Input: (props) => <input {...props} />,
}));

jest.mock("@/components/ui/textarea", () => ({
  Textarea: (props) => <textarea {...props} />,
}));

jest.mock("@/components/ui/label", () => ({
  Label: ({ children, ...props }) => <label {...props}>{children}</label>,
}));

jest.mock("@/components/ui/select", () => {
  const React = require("react");
  const SelectContext = React.createContext(null);
  return {
    Select: ({ children, onValueChange }) => (
      <SelectContext.Provider value={onValueChange}>{children}</SelectContext.Provider>
    ),
    SelectContent: ({ children }) => <div>{children}</div>,
    SelectItem: ({ children, ...props }) => <div {...props}>{children}</div>,
    SelectTrigger: ({ children, ...props }) => {
      const onValueChange = React.useContext(SelectContext);
      return <button {...props} onClick={() => onValueChange?.("class")}>{children}</button>;
    },
    SelectValue: ({ children }) => <span>{children}</span>,
  };
});

jest.mock("@/components/ui/accordion", () => ({
  Accordion: ({ children }) => <div>{children}</div>,
  AccordionContent: ({ children }) => <div>{children}</div>,
  AccordionItem: ({ children }) => <div>{children}</div>,
  AccordionTrigger: ({ children }) => <button type="button">{children}</button>,
}));

jest.mock("@/components/ui/switch", () => ({
  Switch: ({ checked, onCheckedChange, ...props }) => (
    <input
      type="checkbox"
      checked={checked}
      onChange={(event) => onCheckedChange?.(event.target.checked)}
      {...props}
    />
  ),
}));

describe("CardEditor preload dashboard", () => {
  let container;
  let root;

  beforeEach(() => {
    jest.clearAllMocks();
    Element.prototype.scrollIntoView = jest.fn();
    api.post.mockResolvedValue({ data: {} });
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  it("shows preload status per manual and fires POST /library/preload once", async () => {
    api.get.mockImplementation((path) => {
      if (path === "/library/manuals") {
        return Promise.resolve({
          data: {
            manuals: [{
              filename: "manuale_giocatore.pdf",
              title: "Manuale del Giocatore",
              source_language: "it",
              page_count: 320,
              requires_ocr: false,
              job: { status: "completed", percent: 100, records_imported: 42, records_updated: 3, records_flagged: 5 },
            }],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);

    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/crea"]}>
          <Routes>
            <Route path="/crea" element={<CardEditor />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    expect(api.post).toHaveBeenCalledWith("/library/preload");
    expect(container.querySelector('[data-testid="preload-dashboard"]')).not.toBeNull();
    expect(container.textContent).toContain("Manuale del Giocatore");
    expect(container.textContent).toContain("COMPLETATO");
    expect(container.textContent).toContain("Non devi selezionare pagine o confermare passaggi");
  });

  it("starts a Spanish manual automatically without rendering a consent step", async () => {
    api.get.mockImplementation((path) => {
      if (path === "/library/manuals") {
        return Promise.resolve({
          data: {
            manuals: [{
              filename: "manuale_es.pdf",
              title: "Manual Español",
              source_language: "es",
              page_count: 100,
              requires_ocr: false,
              job: null,
            }],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);

    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/crea"]}>
          <Routes>
            <Route path="/crea" element={<CardEditor />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    expect(container.querySelector('[data-testid="grant-translation-consent-manuale_es.pdf"]')).toBeNull();
    expect(container.textContent).not.toContain("CONSENSO RICHIESTO");
    expect(api.post).toHaveBeenCalledWith("/library/preload");
  });

  it("shows retry button when a job has failed", async () => {
    api.get.mockImplementation((path) => {
      if (path === "/library/manuals") {
        return Promise.resolve({
          data: {
            manuals: [{
              filename: "manuale_err.pdf",
              title: "Manuale Errore",
              source_language: "it",
              requires_ocr: false,
              job: { status: "failed", last_error: "Timeout durante l'estrazione." },
            }],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);

    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/crea"]}>
          <Routes>
            <Route path="/crea" element={<CardEditor />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    expect(container.querySelector('[data-testid="retry-preload-manuale_err.pdf"]')).not.toBeNull();
    expect(container.textContent).toContain("ERRORE");
    expect(container.textContent).toContain("Timeout durante l'estrazione.");

    await act(async () => {
      container.querySelector('[data-testid="retry-preload-manuale_err.pdf"]').click();
      await Promise.resolve();
    });

    expect(api.post).toHaveBeenCalledWith("/library/preload", {
      filename: "manuale_err.pdf",
      retry: true,
    });
  });

  it("shows translation retry countdown when translation_retry_at is set", async () => {
    const retryAt = new Date(Date.now() + 45000).toISOString(); // 45 s in the future
    api.get.mockImplementation((path) => {
      if (path === "/library/manuals") {
        return Promise.resolve({
          data: {
            manuals: [{
              filename: "manuale_rl.pdf",
              title: "Manuale Rate-Limited",
              source_language: "es",
              requires_ocr: false,
              job: {
                status: "processing",
                last_error: "translation_rate_limited",
                translation_retry_at: retryAt,
                translation_retry_attempt: 1,
                percent: 50,
                current_page: 5,
                page_count: 10,
              },
            }],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);

    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/crea"]}>
          <Routes>
            <Route path="/crea" element={<CardEditor />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    const countdown = container.querySelector('[data-testid="translation-retry-countdown"]');
    expect(countdown).not.toBeNull();
    expect(countdown.textContent).toMatch(/Traduzione in ripresa/);
    expect(countdown.textContent).toContain("tentativo 1");
  });

  it("does not show translation retry countdown when translation_retry_at is absent", async () => {
    api.get.mockImplementation((path) => {
      if (path === "/library/manuals") {
        return Promise.resolve({
          data: {
            manuals: [{
              filename: "manuale_ok.pdf",
              title: "Manuale OK",
              source_language: "it",
              requires_ocr: false,
              job: {
                status: "processing",
                last_error: "",
                translation_retry_at: null,
                translation_retry_attempt: 0,
                percent: 60,
                current_page: 6,
                page_count: 10,
              },
            }],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);

    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/crea"]}>
          <Routes>
            <Route path="/crea" element={<CardEditor />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    expect(container.querySelector('[data-testid="translation-retry-countdown"]')).toBeNull();
  });

  it("fires preload immediately for a non-Italian manual requiring OCR without any translation consent gate", async () => {
    api.get.mockImplementation((path) => {
      if (path === "/library/manuals") {
        return Promise.resolve({
          data: {
            manuals: [{
              filename: "scansione_es.pdf",
              title: "Manuale Scansione Spagnolo",
              source_language: "es",
              page_count: 80,
              requires_ocr: true,
              job: null,
            }],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);

    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/crea"]}>
          <Routes>
            <Route path="/crea" element={<CardEditor />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    // No consent gate must block the import flow
    expect(container.querySelector('[data-testid="grant-translation-consent-scansione_es.pdf"]')).toBeNull();
    expect(container.textContent).not.toContain("CONSENSO RICHIESTO");
    // Preload fires automatically — the flow does not stop for user confirmation
    expect(api.post).toHaveBeenCalledWith("/library/preload");
    // Dashboard is rendered — the user sees status immediately
    expect(container.querySelector('[data-testid="preload-dashboard"]')).not.toBeNull();
    expect(container.textContent).toContain("Manuale Scansione Spagnolo");
  });
});

describe("CardEditor review scope", () => {
  let container;
  let root;

  beforeEach(() => {
    jest.clearAllMocks();
    Element.prototype.scrollIntoView = jest.fn();
    api.post.mockResolvedValue({ data: {} });
    api.get.mockImplementation((path) => {
      if (path === "/library/manuals") {
        return Promise.resolve({ data: { manuals: [] } });
      }
      if (path === "/library") {
        return Promise.resolve({
          data: {
            records: [{
              id: "review-1",
              name: "Classe da rivedere",
              reference_type: "class",
              source_refs: [{ filename: "manuale del giocatore.pdf", page: 12 }],
              source_language: "es",
              source_name: "Clase original",
              translation_status: "translated",
              needs_review: true,
              is_trusted: false,
            }],
          },
        });
      }
      if (path === "/library/review-1/review") {
        return Promise.resolve({
          data: {
            id: "review-1",
            name: "Classe da rivedere",
            source_language: "es",
            source_name: "Clase original",
            source_refs: [{ filename: "manuale del giocatore.pdf", page: 12, language: "es" }],
            translation_status: "translated",
            review_status: "pending",
            review_notes: "",
            needs_review: true,
            is_trusted: false,
            review_reason: "Traduzione automatica non ancora verificata da una persona.",
            original: { name: "Clase original", full_text: "Testo originale spagnolo." },
            translation: { name: "Classe da rivedere", full_text: "Testo tradotto in italiano." },
            review_history: [{
              reviewer_id: "owner-1",
              reviewer_name: "Mago",
              reviewer_email: "mago@example.com",
              reviewed_at: "2026-08-22T11:00:00+00:00",
              review_status: "needs_review",
              review_notes: "Controllare il termine tecnico.",
            }],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });
    api.patch.mockResolvedValue({
      data: {
        id: "review-1",
        name: "Classe da rivedere",
        source_language: "es",
        source_name: "Clase original",
        source_refs: [{ filename: "manuale del giocatore.pdf", page: 12, language: "es" }],
        translation_status: "translated",
        review_status: "verified",
        review_notes: "Confrontata con il manuale.",
        needs_review: false,
        is_trusted: true,
        review_history: [{
          reviewer_id: "owner-1",
          reviewer_name: "Mago",
          reviewer_email: "mago@example.com",
          reviewed_at: "2026-08-22T11:05:00+00:00",
          review_status: "verified",
          review_notes: "Confrontata con il manuale.",
        }, {
          reviewer_id: "owner-1",
          reviewer_name: "Mago",
          reviewer_email: "mago@example.com",
          reviewed_at: "2026-08-22T11:00:00+00:00",
          review_status: "needs_review",
          review_notes: "Controllare il termine tecnico.",
        }],
      },
    });
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  it("requests only review records from the selected manual and categories", async () => {
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/crea?reviewTypes=class%2Cfeat&reviewManual=manuale%20del%20giocatore.pdf"]}>
          <Routes>
            <Route path="/crea" element={<CardEditor />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 280));
    });

    expect(api.get).toHaveBeenCalledWith("/library", {
      params: {
        types: "class,feat",
        review_only: true,
        include_unverified: true,
        source_filename: "manuale del giocatore.pdf",
      },
    });
    expect(container.textContent).toContain("Classe da rivedere");
  });

  it("keeps the review scope when the card type changes", async () => {
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/crea?reviewTypes=class%2Cfeat&reviewManual=manuale%20del%20giocatore.pdf"]}>
          <Routes>
            <Route path="/crea" element={<CardEditor />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 280));
    });

    const typeSelect = container.querySelector('[data-testid="type-select"]');
    expect(typeSelect).not.toBeNull();

    await act(async () => {
      typeSelect.click();
      await new Promise((resolve) => setTimeout(resolve, 280));
    });

    const libraryCalls = api.get.mock.calls.filter(([path]) => path === "/library");
    expect(libraryCalls).toHaveLength(2);
    expect(libraryCalls[1]).toEqual(["/library", {
      params: {
        types: "class,feat",
        review_only: true,
        include_unverified: true,
        source_filename: "manuale del giocatore.pdf",
      },
    }]);
  });

  it("hides the retry translation button for a record with review_status verified", async () => {
    api.get.mockImplementation((path) => {
      if (path === "/library/manuals") {
        return Promise.resolve({ data: { manuals: [] } });
      }
      if (path === "/library") {
        return Promise.resolve({
          data: {
            records: [{
              id: "verified-1",
              name: "Classe verificata",
              reference_type: "class",
              source_refs: [{ filename: "manuale del giocatore.pdf", page: 5 }],
              source_language: "es",
              source_name: "Clase verificada",
              translation_status: "failed",
              needs_review: false,
              review_status: "verified",
              is_trusted: true,
            }],
          },
        });
      }
      if (path === "/library/verified-1/review") {
        return Promise.resolve({
          data: {
            id: "verified-1",
            name: "Classe verificata",
            source_language: "es",
            source_name: "Clase verificada",
            source_refs: [{ filename: "manuale del giocatore.pdf", page: 5, language: "es" }],
            translation_status: "failed",
            review_status: "verified",
            review_notes: "Confermata manualmente.",
            needs_review: false,
            is_trusted: true,
            review_reason: null,
            original: { name: "Clase verificada", full_text: "Testo originale." },
            translation: { name: "Classe verificata", full_text: "Testo tradotto." },
            review_history: [{
              reviewer_id: "owner-1",
              reviewer_name: "Mago",
              reviewer_email: "mago@example.com",
              reviewed_at: "2026-08-22T12:00:00+00:00",
              review_status: "verified",
              review_notes: "Confermata manualmente.",
            }],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/crea?reviewTypes=class&reviewManual=manuale%20del%20giocatore.pdf"]}>
          <Routes>
            <Route path="/crea" element={<CardEditor />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 280));
    });

    await act(async () => {
      container.querySelector('[data-testid="source-reference-verified-1"]').click();
      await Promise.resolve();
    });

    expect(api.get).toHaveBeenCalledWith("/library/verified-1/review");
    expect(container.querySelector('[data-testid="reference-source-panel"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="retry-reference-translation-verified-1"]')).toBeNull();
  });

  it("compares a Spanish original with its translation and confirms it from review", async () => {
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/crea?reviewTypes=class&reviewManual=manuale%20del%20giocatore.pdf"]}>
          <Routes>
            <Route path="/crea" element={<CardEditor />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 280));
    });

    await act(async () => {
      container.querySelector('[data-testid="source-reference-review-1"]').click();
      await Promise.resolve();
    });

    expect(api.get).toHaveBeenCalledWith("/library/review-1/review");
    expect(container.querySelector('[data-testid="reference-review-panel"]')).not.toBeNull();
    expect(container.textContent).toContain("Testo originale spagnolo.");
    expect(container.textContent).toContain("Testo tradotto in italiano.");
    expect(container.textContent).toContain("manuale del giocatore.pdf · pagina 12");
    expect(container.querySelector('[data-testid="reference-review-history"]')).not.toBeNull();
    expect(container.textContent).toContain("Controllare il termine tecnico.");

    await act(async () => {
      container.querySelector('[data-testid="approve-reference"]').click();
      await Promise.resolve();
    });

    expect(api.patch).toHaveBeenCalledWith("/library/review-1/review", {
      review_status: "verified",
      review_notes: "",
    });
    expect(container.querySelector('[data-testid="reference-review-panel"]')).toBeNull();
    expect(container.textContent).toContain("Confrontata con il manuale.");
    expect(container.textContent).toContain("2 decisioni");
  });

  it("shows Fonte verificata (not BLOCCATO) for a record with verified review_status and failed translation_status", async () => {
    api.get.mockImplementation((path) => {
      if (path === "/library/manuals") {
        return Promise.resolve({ data: { manuals: [] } });
      }
      if (path === "/library") {
        return Promise.resolve({
          data: {
            records: [{
              id: "verified-failed-1",
              name: "Classe Verificata Traduzione Fallita",
              reference_type: "class",
              source_refs: [{ filename: "manuale del giocatore.pdf", page: 10 }],
              source_language: "es",
              source_name: "Clase verificada",
              translation_status: "failed",
              review_status: "verified",
              needs_review: false,
              is_trusted: true,
            }],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/crea?reviewTypes=class&reviewManual=manuale%20del%20giocatore.pdf"]}>
          <Routes>
            <Route path="/crea" element={<CardEditor />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 280));
    });

    expect(container.textContent).toContain("Classe Verificata Traduzione Fallita");
    expect(container.textContent).toContain("Fonte verificata");
    expect(container.textContent).not.toContain("BLOCCATO");

    const applyBtn = container.querySelector('[data-testid="apply-reference-verified-failed-1"]');
    expect(applyBtn).not.toBeNull();
    expect(applyBtn.disabled).toBe(false);

    const applyLabel = applyBtn.closest('[data-testid="apply-reference-verified-failed-1"]')
      ?.parentElement?.textContent;
    expect(applyLabel).not.toContain("BLOCCATO");
  });

  it("clicking APPLICA on a verified+failed record calls POST /library/{id}/apply and succeeds", async () => {
    api.get.mockImplementation((path) => {
      if (path === "/library/manuals") {
        return Promise.resolve({ data: { manuals: [] } });
      }
      if (path === "/library") {
        return Promise.resolve({
          data: {
            records: [{
              id: "verified-failed-1",
              name: "Classe Verificata Traduzione Fallita",
              reference_type: "class",
              source_refs: [{ filename: "manuale del giocatore.pdf", page: 10 }],
              source_language: "es",
              source_name: "Clase verificada",
              translation_status: "failed",
              review_status: "verified",
              needs_review: false,
              is_trusted: true,
            }],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    api.post.mockImplementation((path) => {
      if (path === "/library/verified-failed-1/apply") {
        return Promise.resolve({
          data: {
            reference_id: "verified-failed-1",
            name: "Classe Verificata Traduzione Fallita",
            card_type: "class",
            reference_type: "class",
            attributes: {},
            description: "Descrizione della classe.",
            story: "",
            source_refs: [{ filename: "manuale del giocatore.pdf", page: 10, language: "es" }],
            rule_source: { source_kind: "library", source_id: "verified-failed-1" },
            content_language: "it",
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/crea?reviewTypes=class&reviewManual=manuale%20del%20giocatore.pdf"]}>
          <Routes>
            <Route path="/crea" element={<CardEditor />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 280));
    });

    const applyBtn = container.querySelector('[data-testid="apply-reference-verified-failed-1"]');
    expect(applyBtn).not.toBeNull();
    expect(applyBtn.disabled).toBe(false);

    await act(async () => {
      applyBtn.click();
      await Promise.resolve();
    });

    expect(api.post).toHaveBeenCalledWith("/library/verified-failed-1/apply");

    const { toast } = require("sonner");
    expect(toast.success).toHaveBeenCalledWith("Contenuto applicato dalla biblioteca privata");
  });

  it("apply button is disabled for a record with is_trusted false (needs_review)", async () => {
    api.get.mockImplementation((path) => {
      if (path === "/library/manuals") {
        return Promise.resolve({ data: { manuals: [] } });
      }
      if (path === "/library") {
        return Promise.resolve({
          data: {
            records: [{
              id: "untrusted-1",
              name: "Classe non verificata",
              reference_type: "class",
              source_refs: [{ filename: "manuale del giocatore.pdf", page: 3 }],
              source_language: "es",
              source_name: "Clase original",
              translation_status: "translated",
              review_status: "needs_review",
              needs_review: true,
              is_trusted: false,
              review_reason: "Traduzione automatica non ancora verificata.",
            }],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/crea?reviewTypes=class&reviewManual=manuale%20del%20giocatore.pdf"]}>
          <Routes>
            <Route path="/crea" element={<CardEditor />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 280));
    });

    const applyBtn = container.querySelector('[data-testid="apply-reference-untrusted-1"]');
    expect(applyBtn).not.toBeNull();
    expect(applyBtn.disabled).toBe(true);
    expect(container.textContent).toContain("BLOCCATO");
    expect(container.textContent).not.toContain("APPLICA");
    expect(api.post).not.toHaveBeenCalledWith("/library/untrusted-1/apply");
  });

  it("shows 'Traduzione non disponibile' in the source panel when translation_status is failed and text is absent", async () => {
    api.get.mockImplementation((path) => {
      if (path === "/library/manuals") {
        return Promise.resolve({ data: { manuals: [] } });
      }
      if (path === "/library") {
        return Promise.resolve({
          data: {
            records: [{
              id: "failed-trans-1",
              name: "Classe traduzione fallita",
              reference_type: "class",
              source_refs: [{ filename: "manuale del giocatore.pdf", page: 7 }],
              source_language: "es",
              source_name: "Clase traduccion fallida",
              translation_status: "failed",
              review_status: "needs_review",
              needs_review: true,
              is_trusted: false,
            }],
          },
        });
      }
      if (path === "/library/failed-trans-1/review") {
        return Promise.resolve({
          data: {
            id: "failed-trans-1",
            name: "Classe traduzione fallita",
            source_language: "es",
            source_name: "Clase traduccion fallida",
            source_refs: [{ filename: "manuale del giocatore.pdf", page: 7, language: "es" }],
            translation_status: "failed",
            review_status: "needs_review",
            needs_review: true,
            is_trusted: false,
            review_reason: "Traduzione automatica fallita.",
            original: { name: "Clase traduccion fallida", full_text: "Testo spagnolo originale." },
            translation: null,
            full_text: null,
            review_history: [],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/crea?reviewTypes=class&reviewManual=manuale%20del%20giocatore.pdf"]}>
          <Routes>
            <Route path="/crea" element={<CardEditor />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 280));
    });

    await act(async () => {
      container.querySelector('[data-testid="source-reference-failed-trans-1"]').click();
      await Promise.resolve();
    });

    expect(api.get).toHaveBeenCalledWith("/library/failed-trans-1/review");
    expect(container.querySelector('[data-testid="reference-source-panel"]')).not.toBeNull();
    const translationArticle = container.querySelector('[data-testid="reference-translation"]');
    expect(translationArticle).not.toBeNull();
    expect(translationArticle.textContent).toContain("Traduzione non disponibile.");
  });

  it("shows translation-failed-verified-notice badge when review_status is verified and translation_status is failed", async () => {
    api.get.mockImplementation((path) => {
      if (path === "/library/manuals") {
        return Promise.resolve({ data: { manuals: [] } });
      }
      if (path === "/library") {
        return Promise.resolve({
          data: {
            records: [{
              id: "verified-badge-1",
              name: "Classe Verificata Errore",
              reference_type: "class",
              source_refs: [{ filename: "manuale del giocatore.pdf", page: 2 }],
              source_language: "es",
              source_name: "Clase verificada",
              translation_status: "failed",
              translation_error: "provider_rate_limited",
              review_status: "verified",
              needs_review: false,
              is_trusted: true,
            }],
          },
        });
      }
      if (path === "/library/verified-badge-1/review") {
        return Promise.resolve({
          data: {
            id: "verified-badge-1",
            name: "Classe Verificata Errore",
            source_language: "es",
            source_name: "Clase verificada",
            source_refs: [{ filename: "manuale del giocatore.pdf", page: 2, language: "es" }],
            translation_status: "failed",
            translation_error: "provider_rate_limited",
            review_status: "verified",
            review_notes: "Verificata manualmente.",
            needs_review: false,
            is_trusted: true,
            review_reason: null,
            original: { name: "Clase verificada", full_text: "Testo spagnolo." },
            translation: { name: "Classe Verificata Errore", full_text: "Testo italiano verificato." },
            review_history: [{
              reviewer_id: "owner-1",
              reviewer_name: "Mago",
              reviewer_email: "mago@example.com",
              reviewed_at: "2026-08-22T12:00:00+00:00",
              review_status: "verified",
              review_notes: "Verificata manualmente.",
            }],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/crea?reviewTypes=class&reviewManual=manuale%20del%20giocatore.pdf"]}>
          <Routes>
            <Route path="/crea" element={<CardEditor />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 280));
    });

    await act(async () => {
      container.querySelector('[data-testid="source-reference-verified-badge-1"]').click();
      await Promise.resolve();
    });

    expect(api.get).toHaveBeenCalledWith("/library/verified-badge-1/review");
    expect(container.querySelector('[data-testid="reference-source-panel"]')).not.toBeNull();
    const badge = container.querySelector('[data-testid="translation-failed-verified-notice"]');
    expect(badge).not.toBeNull();
    expect(badge.textContent).toContain("La traduzione automatica ha avuto un errore ma il tuo contenuto manuale è confermato.");
    // Retry translation button must NOT appear for verified records
    expect(container.querySelector('[data-testid="retry-reference-translation-verified-badge-1"]')).toBeNull();
  });
});