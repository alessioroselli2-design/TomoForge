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

describe("CardEditor review scope", () => {
  let container;
  let root;

  beforeEach(() => {
    jest.clearAllMocks();
    Element.prototype.scrollIntoView = jest.fn();
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
});