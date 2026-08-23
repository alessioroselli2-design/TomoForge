import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { api } from "@/lib/api";
import LibraryCoverageReadiness from "./LibraryCoverageReadiness";

global.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock("@/lib/api", () => ({
  api: { get: jest.fn() },
}));

const coverage = {
  manuals: [{
    filename: "manuale-giocatore.pdf",
    title: "Manuale del Giocatore",
    source_text: "Testo sorgente riservato che non deve apparire nel riepilogo",
    source_language: "it",
    categories: [
      { reference_type: "class", valid: 2, to_review: 1, missing: 0, records_total: 3 },
      { reference_type: "feat", valid: 0, to_review: 0, missing: 1, records_total: 0 },
    ],
  }],
  totals: { valid: 2, to_review: 1, missing: 1, translation_pending: 0 },
};

// Wrap in MemoryRouter because the component renders <Link> for import
// suggestions and the pending-translation strip.
function renderInRouter(element) {
  return <MemoryRouter>{element}</MemoryRouter>;
}

describe("LibraryCoverageReadiness", () => {
  let container;
  let root;

  beforeEach(() => {
    jest.clearAllMocks();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  it("summarises private coverage and opens only existing review records", async () => {
    api.get.mockResolvedValue({ data: coverage });
    const onOpenReviews = jest.fn();

    await act(async () => {
      root.render(renderInRouter(<LibraryCoverageReadiness onOpenReviews={onOpenReviews} />));
      await Promise.resolve();
    });

    expect(api.get).toHaveBeenCalledWith("/library/coverage");
    expect(container.textContent).toContain("Cosa puoi usare con fiducia");
    expect(container.textContent).toContain("CATEGORIE SENZA RECORD");
    expect(container.textContent).not.toContain("manuale-giocatore.pdf");
    expect(container.textContent).not.toContain("Testo sorgente riservato");

    await act(async () => {
      [...container.querySelectorAll("button")].find((button) => button.textContent.includes("Manuale del Giocatore")).click();
    });

    expect(container.textContent).toContain("Classi");
    expect(container.textContent).toContain("UTILIZZABILE");
    expect(container.textContent).toContain("Talenti");
    expect(container.textContent).toContain("NON DISPONIBILE");
    expect(container.textContent).toContain("nessun record");

    await act(async () => {
      [...container.querySelectorAll("button")].find((button) => button.textContent === "REVISIONI").click();
    });
    expect(onOpenReviews).toHaveBeenCalledWith("class", "manuale-giocatore.pdf");
  });

  it("offers a retry when the private report is unavailable", async () => {
    api.get.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({ data: coverage });

    await act(async () => {
      root.render(renderInRouter(<LibraryCoverageReadiness />));
      await Promise.resolve();
    });

    expect(container.textContent).toContain("REGISTRO DI PRONTEZZA NON DISPONIBILE");
    const retry = [...container.querySelectorAll("button")].find((button) => button.textContent.includes("RIPROVA"));
    await act(async () => {
      retry.click();
      await Promise.resolve();
    });

    expect(api.get).toHaveBeenCalledTimes(2);
    expect(container.textContent).toContain("Cosa puoi usare con fiducia");
  });

  it("shows loading and an empty state without manual data", async () => {
    api.get.mockImplementationOnce(() => new Promise(() => {}));

    await act(async () => {
      root.render(renderInRouter(<LibraryCoverageReadiness />));
      await Promise.resolve();
    });
    expect(container.querySelector('[data-testid="library-coverage-loading"]')).not.toBeNull();

    await act(async () => root.unmount());
    root = createRoot(container);
    api.get.mockResolvedValueOnce({ data: { manuals: [], totals: { valid: 0, to_review: 0, missing: 0, translation_pending: 0 } } });

    await act(async () => {
      root.render(renderInRouter(<LibraryCoverageReadiness />));
      await Promise.resolve();
    });
    expect(container.querySelector('[data-testid="library-coverage-empty"]')).not.toBeNull();
    expect(container.textContent).toContain("precaricati automaticamente");
  });

  it("calls onTotalsChange with the totals when coverage loads", async () => {
    api.get.mockResolvedValue({ data: coverage });
    const onTotalsChange = jest.fn();

    await act(async () => {
      root.render(renderInRouter(<LibraryCoverageReadiness onTotalsChange={onTotalsChange} />));
      await Promise.resolve();
    });

    expect(onTotalsChange).toHaveBeenCalledTimes(1);
    expect(onTotalsChange).toHaveBeenCalledWith(
      expect.objectContaining({ valid: 2, to_review: 1, missing: 1, translation_pending: 0 })
    );
  });

  it("shows an amber strip when translation_pending > 0 and links to the import dashboard", async () => {
    const dataWithPending = {
      ...coverage,
      totals: { valid: 2, to_review: 0, missing: 0, translation_pending: 3 },
    };
    api.get.mockResolvedValue({ data: dataWithPending });

    await act(async () => {
      root.render(renderInRouter(<LibraryCoverageReadiness />));
      await Promise.resolve();
    });

    const strip = container.querySelector('[data-testid="coverage-translation-pending-strip"]');
    expect(strip).not.toBeNull();
    expect(strip.textContent).toContain("3 TRADUZIONI IN SOSPESO");
    // Link must point to the import dashboard
    const link = strip.querySelector("a");
    expect(link).not.toBeNull();
    expect(link.getAttribute("href")).toBe("/crea#editor-library-import");
  });

  it("does not show the pending strip when translation_pending is zero", async () => {
    api.get.mockResolvedValue({ data: coverage }); // translation_pending: 0

    await act(async () => {
      root.render(renderInRouter(<LibraryCoverageReadiness />));
      await Promise.resolve();
    });

    expect(container.querySelector('[data-testid="coverage-translation-pending-strip"]')).toBeNull();
  });

  it("shows an import link for empty categories when the manual row is expanded", async () => {
    api.get.mockResolvedValue({ data: coverage });

    await act(async () => {
      root.render(renderInRouter(<LibraryCoverageReadiness />));
      await Promise.resolve();
    });

    // Expand the manual row
    await act(async () => {
      [...container.querySelectorAll("button")]
        .find((b) => b.textContent.includes("Manuale del Giocatore"))
        .click();
    });

    // The "Talenti" (feat) category has missing=1, no valid/to_review —
    // it should show an "Avvia importazione" link.
    const importLinks = [...container.querySelectorAll("a")].filter(
      (a) => a.textContent.includes("importazione")
    );
    expect(importLinks.length).toBeGreaterThan(0);
    expect(importLinks[0].getAttribute("href")).toBe("/crea#editor-library-import");
  });
});
