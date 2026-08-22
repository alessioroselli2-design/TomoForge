import React, { act } from "react";
import { createRoot } from "react-dom/client";
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
  totals: { valid: 2, to_review: 1, missing: 1 },
};

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
      root.render(<LibraryCoverageReadiness onOpenReviews={onOpenReviews} />);
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
      root.render(<LibraryCoverageReadiness />);
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
      root.render(<LibraryCoverageReadiness />);
      await Promise.resolve();
    });
    expect(container.querySelector('[data-testid="library-coverage-loading"]')).not.toBeNull();

    await act(async () => root.unmount());
    root = createRoot(container);
    api.get.mockResolvedValueOnce({ data: { manuals: [], totals: { valid: 0, to_review: 0, missing: 0 } } });

    await act(async () => {
      root.render(<LibraryCoverageReadiness />);
      await Promise.resolve();
    });
    expect(container.querySelector('[data-testid="library-coverage-empty"]')).not.toBeNull();
    expect(container.textContent).toContain("precaricati automaticamente");
  });
});