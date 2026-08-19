import React, { act } from "react";
import { createRoot } from "react-dom/client";
import jsPDF from "jspdf";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { api } from "@/lib/api";
import { addSingleCardA4PdfPages } from "@/lib/cardExport";
import CardDetail from "./CardDetail";

global.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  },
}));

jest.mock("@/lib/cardExport", () => ({
  createCardPng: jest.fn(),
  addSingleCardPdfPages: jest.fn(),
  addSingleCardA4PdfPages: jest.fn(async (pdf) => {
    pdf.addImage("front", "PNG", 0, 0, 190, 277);
    pdf.addPage();
    pdf.addImage("back", "PNG", 0, 0, 190, 277);
  }),
}));

jest.mock("jspdf", () => jest.fn());

jest.mock("@/components/Navbar", () => () => {
  const React = require("react");
  return React.createElement("nav");
});

jest.mock("@/components/TradingCard", () => {
  const React = require("react");
  return {
    CardFront: ({ card, exportMode }) => React.createElement(
      "div",
      { "data-testid": exportMode ? "export-front" : "card-front" },
      card.name,
    ),
    CardBack: () => React.createElement("div", { "data-testid": "card-back" }),
  };
});

jest.mock("framer-motion", () => {
  const React = require("react");
  const MotionDiv = ({ children, animate, transition, ...props }) => (
    React.createElement("div", props, children)
  );
  return { motion: { div: MotionDiv } };
});

jest.mock("sonner", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock("@/components/ui/alert-dialog", () => {
  const React = require("react");
  const passthrough = ({ children }) => React.createElement(React.Fragment, null, children);
  const content = ({ children, ...props }) => React.createElement("div", props, children);
  const action = ({ children, ...props }) => React.createElement("button", props, children);
  return {
    AlertDialog: passthrough,
    AlertDialogAction: action,
    AlertDialogCancel: action,
    AlertDialogContent: content,
    AlertDialogDescription: content,
    AlertDialogFooter: content,
    AlertDialogHeader: content,
    AlertDialogTitle: content,
    AlertDialogTrigger: passthrough,
  };
});

const loadedCard = {
  id: "card-123",
  type: "spell",
  name: "Tempesta del Drago Cremisi",
  frame: "gold",
  appearance: {},
  attributes: {},
  back: { style: "runic", color: "#2563eb", emblem: "dragon", motto: "Sempre avanti" },
};

describe("CardDetail A4 export action", () => {
  let container;
  let root;
  let pdf;

  beforeEach(() => {
    jest.clearAllMocks();
    pdf = {
      addImage: jest.fn(),
      addPage: jest.fn(),
      save: jest.fn(),
    };
    jsPDF.mockImplementation(() => pdf);
    addSingleCardA4PdfPages.mockImplementation(async (activePdf) => {
      activePdf.addImage("front", "PNG", 0, 0, 190, 277);
      activePdf.addPage();
      activePdf.addImage("back", "PNG", 0, 0, 190, 277);
    });
    api.get.mockResolvedValue({ data: loadedCard });
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  it("routes the loaded card's A4 action through the shared two-page export adapter", async () => {
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={["/carta/card-123"]}>
          <Routes>
            <Route path="/carta/:id" element={<CardDetail />} />
          </Routes>
        </MemoryRouter>,
      );
      await Promise.resolve();
    });

    const sheetButton = container.querySelector('[data-testid="sheet-btn"]');
    expect(sheetButton).not.toBeNull();
    expect(api.get).toHaveBeenCalledWith("/cards/card-123");

    await act(async () => {
      sheetButton.click();
      await Promise.resolve();
    });

    expect(jsPDF).toHaveBeenCalledWith({
      orientation: "portrait",
      unit: "mm",
      format: "a4",
    });
    expect(addSingleCardA4PdfPages).toHaveBeenCalledWith(
      pdf,
      container.querySelector('[data-testid="export-front"]').parentElement,
      loadedCard,
    );
    expect(pdf.addImage).toHaveBeenCalledTimes(2);
    expect(pdf.addPage).toHaveBeenCalledTimes(1);
    expect(pdf.save).toHaveBeenCalledWith(
      "carta-Tempesta del Drago Cremisi-a4-fronte-retro.pdf",
    );
  });
});