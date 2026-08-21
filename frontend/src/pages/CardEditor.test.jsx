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

jest.mock("@/components/ui/select", () => ({
  Select: ({ children }) => <div>{children}</div>,
  SelectContent: ({ children }) => <div>{children}</div>,
  SelectItem: ({ children, ...props }) => <div {...props}>{children}</div>,
  SelectTrigger: ({ children, ...props }) => <button {...props}>{children}</button>,
  SelectValue: ({ children }) => <span>{children}</span>,
}));

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
            }],
          },
        });
      }
      return Promise.resolve({ data: {} });
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
});