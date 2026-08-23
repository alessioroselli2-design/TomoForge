import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { api } from "@/lib/api";
import LibraryCoverageReadiness from "./LibraryCoverageReadiness";

global.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock("@/lib/api", () => ({
  api: { get: jest.fn() },
}));

jest.mock("lucide-react", () => ({
  AlertCircle: () => null,
  AlertTriangle: () => null,
  Check: () => null,
  ChevronDown: () => null,
  ChevronUp: () => null,
  CircleDashed: () => null,
  RefreshCw: () => null,
  ShieldCheck: () => null,
}));

jest.mock("@/components/ui/button", () => ({
  Button: ({ children, ...props }) => <button {...props}>{children}</button>,
}));

describe("LibraryCoverageReadiness", () => {
  let container;
  let root;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  function renderComponent(props = {}) {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    return act(async () => {
      root.render(
        <MemoryRouter>
          <LibraryCoverageReadiness {...props} />
        </MemoryRouter>,
      );
      await Promise.resolve();
    });
  }

  async function expandFirstManual() {
    // The coverage section has an "AGGIORNA" refresh button first, then the
    // per-manual expand buttons. Click the second button (index 1) to open
    // the first manual's category detail rows.
    await act(async () => {
      const buttons = container.querySelectorAll('[data-testid="library-coverage"] button');
      // buttons[0] = AGGIORNA (refresh), buttons[1] = first manual expand row
      const expandBtn = buttons[1];
      expandBtn.click();
      await Promise.resolve();
    });
  }

  it("shows all categories as UTILIZZABILE (green) when every record is trusted", async () => {
    api.get.mockResolvedValue({
      data: {
        totals: { valid: 10, to_review: 0, missing: 0, translation_pending: 0 },
        manuals: [{
          filename: "manuale_it.pdf",
          title: "Manuale del Giocatore",
          source_language: "it",
          categories: [
            { reference_type: "class", valid: 5, to_review: 0, missing: 0 },
            { reference_type: "spell", valid: 5, to_review: 0, missing: 0 },
          ],
        }],
      },
    });

    await renderComponent();

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    expect(api.get).toHaveBeenCalledWith("/library/coverage");
    expect(container.querySelector('[data-testid="library-coverage"]')).not.toBeNull();

    // Expand the manual to reveal category rows
    await expandFirstManual();

    expect(container.textContent).toContain("UTILIZZABILE");
    expect(container.textContent).not.toContain("RICHIEDE REVISIONE");
    expect(container.textContent).not.toContain("NON DISPONIBILE");

    // Top-level totals: valid count shown, to_review and missing are 0
    expect(container.textContent).toContain("10");
  });

  it("shows categories as RICHIEDE REVISIONE (amber) when some records need review", async () => {
    api.get.mockResolvedValue({
      data: {
        totals: { valid: 5, to_review: 3, missing: 0, translation_pending: 0 },
        manuals: [{
          filename: "manuale_es.pdf",
          title: "Manuale Spagnolo",
          source_language: "es",
          categories: [
            { reference_type: "class", valid: 5, to_review: 0, missing: 0 },
            { reference_type: "feat", valid: 0, to_review: 3, missing: 0 },
          ],
        }],
      },
    });

    await renderComponent();

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    expect(container.querySelector('[data-testid="library-coverage"]')).not.toBeNull();

    // Expand the manual to reveal category rows
    await expandFirstManual();

    // One category is green (class), one is amber (feat)
    expect(container.textContent).toContain("UTILIZZABILE");
    expect(container.textContent).toContain("RICHIEDE REVISIONE");
    expect(container.textContent).not.toContain("NON DISPONIBILE");

    // Top-level to_review count is shown
    expect(container.textContent).toContain("3");
  });

  it("shows categories as NON DISPONIBILE (red) when categories have no records", async () => {
    api.get.mockResolvedValue({
      data: {
        totals: { valid: 0, to_review: 0, missing: 2, translation_pending: 0 },
        manuals: [{
          filename: "manuale_vuoto.pdf",
          title: "Manuale Vuoto",
          source_language: "it",
          categories: [
            { reference_type: "class", valid: 0, to_review: 0, missing: 1 },
            { reference_type: "race", valid: 0, to_review: 0, missing: 1 },
          ],
        }],
      },
    });

    await renderComponent();

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    expect(container.querySelector('[data-testid="library-coverage"]')).not.toBeNull();

    // Expand the manual to reveal category rows
    await expandFirstManual();

    // Both categories show NON DISPONIBILE
    expect(container.textContent).toContain("NON DISPONIBILE");
    expect(container.textContent).not.toContain("UTILIZZABILE");
    expect(container.textContent).not.toContain("RICHIEDE REVISIONE");

    // Missing count shown in the totals grid
    expect(container.textContent).toContain("2");
  });

  it("shows the translation-pending strip when totals.translation_pending is greater than zero", async () => {
    api.get.mockResolvedValue({
      data: {
        totals: { valid: 4, to_review: 0, missing: 0, translation_pending: 2 },
        manuals: [{
          filename: "manuale_pending.pdf",
          title: "Manuale Pending",
          source_language: "es",
          categories: [
            { reference_type: "class", valid: 4, to_review: 0, missing: 0 },
          ],
        }],
      },
    });

    await renderComponent();

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    const strip = container.querySelector('[data-testid="coverage-translation-pending-strip"]');
    expect(strip).not.toBeNull();
    expect(strip.textContent).toContain("2 TRADUZIONI IN SOSPESO");
  });

  it("shows the empty-state section when the manuals list is empty", async () => {
    api.get.mockResolvedValue({
      data: {
        totals: { valid: 0, to_review: 0, missing: 0, translation_pending: 0 },
        manuals: [],
      },
    });

    await renderComponent();

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    expect(container.querySelector('[data-testid="library-coverage-empty"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="library-coverage"]')).toBeNull();
  });
});
