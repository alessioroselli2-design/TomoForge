import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";

import { api } from "@/lib/api";
import ReferenceReview from "./ReferenceReview";

global.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock("@/lib/api", () => ({
  api: { get: jest.fn(), patch: jest.fn() },
}));

jest.mock("@/components/Navbar", () => () => <nav />);

jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));

describe("ReferenceReview", () => {
  let container;
  let root;

  beforeEach(() => {
    jest.clearAllMocks();
    const queueRecord = {
      id: "ocr-1",
      name: "Guerriero Ocr",
      reference_type: "class",
      source_refs: [{ filename: "Manuale.pdf", page: 12 }],
      needs_review: true,
    };
    api.get.mockImplementation((path) => {
      if (path === "/library") {
        return Promise.resolve({ data: { records: [queueRecord] } });
      }
      if (path === "/library/ocr-1/review") {
        return Promise.resolve({
          data: {
            ...queueRecord,
            source_language: "it",
            review_notes: "",
            review_reason: "Trascrizione OCR non verificata da una persona.",
            original: {
              name: "Guerriero Ocr",
              full_text: "Testo OCR impreciso.",
              attributes: { dado_vita: "d10" },
            },
            translation: {
              name: "Guerriero Ocr",
              description: "Descrizione imprecisa.",
              full_text: "Testo OCR impreciso.",
              attributes: { dado_vita: "d10" },
            },
            review_history: [],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });
    api.patch.mockResolvedValue({ data: { id: "ocr-1", review_status: "verified" } });
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  it("loads the filtered queue, edits OCR fields, and verifies the record", async () => {
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/revisioni?types=class&source=Manuale.pdf"]}>
          <ReferenceReview />
        </MemoryRouter>,
      );
      await Promise.resolve();
    });
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 10)); });
    await act(async () => { await Promise.resolve(); });
    await act(async () => { await Promise.resolve(); });

    expect(api.get).toHaveBeenCalledWith("/library", {
      params: {
        types: "class",
        source_filename: "Manuale.pdf",
        review_only: true,
        include_unverified: true,
        limit: 8000,
      },
    });
    expect(container.textContent).toContain("Manuale.pdf · pagina 12");

    const name = container.querySelector('[data-testid="review-name"]');
    await act(async () => {
      const valueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
      valueSetter.call(name, "Guerriero");
      name.dispatchEvent(new Event("input", { bubbles: true }));
    });

    await act(async () => {
      container.querySelector('[data-testid="verify-review-record"]').click();
      await Promise.resolve();
    });

    expect(api.patch).toHaveBeenCalledWith("/library/ocr-1/review", {
      review_status: "verified",
      review_notes: "",
      name: "Guerriero",
      description: "Descrizione imprecisa.",
      full_text: "Testo OCR impreciso.",
      attributes: { dado_vita: "d10" },
    });
    expect(container.textContent).toContain("Coda completata");
  });
});