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

const reviewRecords = [
  { id: "r1", name: "Barbaro", reference_type: "class" },
  { id: "r2", name: "Ladro", reference_type: "class" },
];

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
      [...container.querySelectorAll("button")].find((b) => b.textContent.includes("Manuale del Giocatore")).click();
    });

    expect(container.textContent).toContain("Classi");
    expect(container.textContent).toContain("UTILIZZABILE");
    expect(container.textContent).toContain("Talenti");
    expect(container.textContent).toContain("NON DISPONIBILE");
    expect(container.textContent).toContain("nessun record");
  });

  it("offers a retry when the private report is unavailable", async () => {
    api.get.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({ data: coverage });

    await act(async () => {
      root.render(renderInRouter(<LibraryCoverageReadiness />));
      await Promise.resolve();
    });

    expect(container.textContent).toContain("REGISTRO DI PRONTEZZA NON DISPONIBILE");
    const retry = [...container.querySelectorAll("button")].find((b) => b.textContent.includes("RIPROVA"));
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
    const link = strip.querySelector("a");
    expect(link).not.toBeNull();
    expect(link.getAttribute("href")).toBe("/crea#editor-library-import");
  });

  it("does not show the pending strip when translation_pending is zero", async () => {
    api.get.mockResolvedValue({ data: coverage });

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

    await act(async () => {
      [...container.querySelectorAll("button")]
        .find((b) => b.textContent.includes("Manuale del Giocatore"))
        .click();
    });

    const importLinks = [...container.querySelectorAll("a")].filter(
      (a) => a.textContent.includes("importazione")
    );
    expect(importLinks.length).toBeGreaterThan(0);
    expect(importLinks[0].getAttribute("href")).toBe("/crea#editor-library-import");
  });

  // ── Inline category record list ──────────────────────────────────────────

  it("expands a 'RICHIEDE REVISIONE' category and shows fetched record names", async () => {
    // First call: coverage; second call: category records
    api.get
      .mockResolvedValueOnce({ data: coverage })
      .mockResolvedValueOnce({ data: { records: reviewRecords, status: "sourced" } });

    const onOpenReviews = jest.fn();

    await act(async () => {
      root.render(renderInRouter(<LibraryCoverageReadiness onOpenReviews={onOpenReviews} />));
      await Promise.resolve();
    });

    // Open the manual row
    await act(async () => {
      [...container.querySelectorAll("button")]
        .find((b) => b.textContent.includes("Manuale del Giocatore"))
        .click();
    });

    // Click the REVISIONI / expand toggle for the "class" category
    const expandBtn = container.querySelector(
      '[data-testid="expand-category-manuale-giocatore.pdf-class"]'
    );
    expect(expandBtn).not.toBeNull();

    await act(async () => {
      expandBtn.click();
      await Promise.resolve();
    });

    // API must be called with review_only + correct filters
    expect(api.get).toHaveBeenCalledWith("/library", {
      params: {
        types: "class",
        source_filename: "manuale-giocatore.pdf",
        review_only: true,
        include_unverified: true,
      },
    });

    // Record list container is visible
    const list = container.querySelector(
      '[data-testid="category-records-list-manuale-giocatore.pdf-class"]'
    );
    expect(list).not.toBeNull();

    // Both record names appear
    expect(list.textContent).toContain("Barbaro");
    expect(list.textContent).toContain("Ladro");

    // Each record has a "Rivedi →" button
    const items = list.querySelectorAll('[data-testid^="category-record-item-"]');
    expect(items.length).toBe(2);
  });

  it("does not re-fetch when the same category is expanded a second time", async () => {
    api.get
      .mockResolvedValueOnce({ data: coverage })
      .mockResolvedValueOnce({ data: { records: reviewRecords, status: "sourced" } });

    await act(async () => {
      root.render(renderInRouter(<LibraryCoverageReadiness />));
      await Promise.resolve();
    });

    await act(async () => {
      [...container.querySelectorAll("button")]
        .find((b) => b.textContent.includes("Manuale del Giocatore"))
        .click();
    });

    const expandBtn = container.querySelector(
      '[data-testid="expand-category-manuale-giocatore.pdf-class"]'
    );

    // First expand → fetches
    await act(async () => {
      expandBtn.click();
      await Promise.resolve();
    });

    // Collapse
    await act(async () => {
      expandBtn.click();
    });

    // Re-expand → must NOT call the API again
    await act(async () => {
      expandBtn.click();
      await Promise.resolve();
    });

    // Only the initial coverage call + one category call = 2 total
    expect(api.get).toHaveBeenCalledTimes(2);

    const list = container.querySelector(
      '[data-testid="category-records-list-manuale-giocatore.pdf-class"]'
    );
    expect(list).not.toBeNull();
    expect(list.textContent).toContain("Barbaro");
  });

  it("clicking 'Rivedi →' on a record calls onOpenReviews with type and filename", async () => {
    api.get
      .mockResolvedValueOnce({ data: coverage })
      .mockResolvedValueOnce({ data: { records: reviewRecords, status: "sourced" } });

    const onOpenReviews = jest.fn();

    await act(async () => {
      root.render(renderInRouter(<LibraryCoverageReadiness onOpenReviews={onOpenReviews} />));
      await Promise.resolve();
    });

    await act(async () => {
      [...container.querySelectorAll("button")]
        .find((b) => b.textContent.includes("Manuale del Giocatore"))
        .click();
    });

    await act(async () => {
      container
        .querySelector('[data-testid="expand-category-manuale-giocatore.pdf-class"]')
        .click();
      await Promise.resolve();
    });

    // Click the first "Rivedi →" button
    const firstItem = container.querySelector('[data-testid="category-record-item-r1"]');
    expect(firstItem).not.toBeNull();
    const riviediBtn = [...firstItem.querySelectorAll("button")].find((b) =>
      b.textContent.includes("Rivedi")
    );
    await act(async () => { riviediBtn.click(); });

    expect(onOpenReviews).toHaveBeenCalledWith("class", "manuale-giocatore.pdf");
  });

  it("shows an overflow link when more than 5 records need review", async () => {
    const manyRecords = Array.from({ length: 8 }, (_, i) => ({
      id: `r${i}`,
      name: `Record ${i}`,
      reference_type: "class",
    }));

    api.get
      .mockResolvedValueOnce({ data: coverage })
      .mockResolvedValueOnce({ data: { records: manyRecords, status: "sourced" } });

    const onOpenReviews = jest.fn();

    await act(async () => {
      root.render(renderInRouter(<LibraryCoverageReadiness onOpenReviews={onOpenReviews} />));
      await Promise.resolve();
    });

    await act(async () => {
      [...container.querySelectorAll("button")]
        .find((b) => b.textContent.includes("Manuale del Giocatore"))
        .click();
    });

    await act(async () => {
      container
        .querySelector('[data-testid="expand-category-manuale-giocatore.pdf-class"]')
        .click();
      await Promise.resolve();
    });

    // Only 5 items shown
    const items = container.querySelectorAll('[data-testid^="category-record-item-"]');
    expect(items.length).toBe(5);

    // Overflow link present and shows correct count
    const overflow = container.querySelector(
      '[data-testid="category-records-overflow-manuale-giocatore.pdf-class"]'
    );
    expect(overflow).not.toBeNull();
    expect(overflow.textContent).toContain("e altri 3");

    // Clicking overflow navigates to the full review list
    await act(async () => { overflow.click(); });
    expect(onOpenReviews).toHaveBeenCalledWith("class", "manuale-giocatore.pdf");
  });

  it("shows an error state when the category record fetch fails", async () => {
    api.get
      .mockResolvedValueOnce({ data: coverage })
      .mockRejectedValueOnce(new Error("network error"));

    await act(async () => {
      root.render(renderInRouter(<LibraryCoverageReadiness />));
      await Promise.resolve();
    });

    await act(async () => {
      [...container.querySelectorAll("button")]
        .find((b) => b.textContent.includes("Manuale del Giocatore"))
        .click();
    });

    await act(async () => {
      container
        .querySelector('[data-testid="expand-category-manuale-giocatore.pdf-class"]')
        .click();
      await Promise.resolve();
    });

    const list = container.querySelector(
      '[data-testid="category-records-list-manuale-giocatore.pdf-class"]'
    );
    expect(list).not.toBeNull();
    expect(list.textContent).toContain("Impossibile caricare");
  });

  it("reloads coverage when the parent increments refreshKey", async () => {
    const updatedCoverage = {
      manuals: [{
        filename: "manuale-giocatore.pdf",
        title: "Manuale del Giocatore",
        source_language: "it",
        categories: [
          { reference_type: "class", valid: 5, to_review: 0, missing: 0, records_total: 5 },
        ],
      }],
      totals: { valid: 5, to_review: 0, missing: 0, translation_pending: 0 },
    };

    api.get
      .mockResolvedValueOnce({ data: coverage })           // 1: initial load (refreshKey=0)
      .mockResolvedValueOnce({ data: updatedCoverage });   // 2: reload (refreshKey=1)

    const onTotalsChange = jest.fn();

    // Initial render with refreshKey=0
    await act(async () => {
      root.render(renderInRouter(
        <LibraryCoverageReadiness refreshKey={0} onTotalsChange={onTotalsChange} />
      ));
      await Promise.resolve();
    });

    expect(api.get).toHaveBeenCalledTimes(1);
    expect(container.textContent).toContain("Cosa puoi usare con fiducia");
    expect(onTotalsChange).toHaveBeenCalledTimes(1);
    expect(onTotalsChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ valid: 2, to_review: 1, missing: 1 })
    );

    // Parent increments refreshKey → must trigger a second coverage fetch
    await act(async () => {
      root.render(renderInRouter(
        <LibraryCoverageReadiness refreshKey={1} onTotalsChange={onTotalsChange} />
      ));
      await Promise.resolve();
    });

    expect(api.get).toHaveBeenCalledTimes(2);
    // onTotalsChange called again with the new totals
    expect(onTotalsChange).toHaveBeenCalledTimes(2);
    expect(onTotalsChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ valid: 5, to_review: 0, missing: 0 })
    );
    // Panel still renders correctly after reload
    expect(container.textContent).toContain("Cosa puoi usare con fiducia");
  });

  it("retries the category record fetch when the user collapses and re-expands after an error", async () => {
    api.get
      .mockResolvedValueOnce({ data: coverage })                                            // 1: coverage
      .mockRejectedValueOnce(new Error("network error"))                                   // 2: first expand → fails
      .mockResolvedValueOnce({ data: { records: reviewRecords, status: "sourced" } });     // 3: retry → succeeds

    await act(async () => {
      root.render(renderInRouter(<LibraryCoverageReadiness />));
      await Promise.resolve();
    });

    // Open the manual row
    await act(async () => {
      [...container.querySelectorAll("button")]
        .find((b) => b.textContent.includes("Manuale del Giocatore"))
        .click();
    });

    const expandBtn = container.querySelector(
      '[data-testid="expand-category-manuale-giocatore.pdf-class"]'
    );

    // First expand → triggers fetch that fails
    await act(async () => {
      expandBtn.click();
      await Promise.resolve();
    });

    // Error message must be visible
    const list = container.querySelector(
      '[data-testid="category-records-list-manuale-giocatore.pdf-class"]'
    );
    expect(list).not.toBeNull();
    expect(list.textContent).toContain("Impossibile caricare");

    // Collapse the category (cache guard key was deleted on error)
    await act(async () => {
      expandBtn.click();
    });

    // Re-expand → must trigger a new API call
    await act(async () => {
      expandBtn.click();
      await Promise.resolve();
    });

    // Three api.get calls total: coverage + first (failed) + retry (success)
    expect(api.get).toHaveBeenCalledTimes(3);

    // Records are now rendered correctly
    const retryList = container.querySelector(
      '[data-testid="category-records-list-manuale-giocatore.pdf-class"]'
    );
    expect(retryList).not.toBeNull();
    expect(retryList.textContent).toContain("Barbaro");
    expect(retryList.textContent).toContain("Ladro");
    expect(retryList.textContent).not.toContain("Impossibile caricare");
  });
});
