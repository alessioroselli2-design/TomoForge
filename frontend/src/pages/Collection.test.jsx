import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { api } from "@/lib/api";
import Collection from "./Collection";

global.IS_REACT_ACT_ENVIRONMENT = true;

const mockNavigate = jest.fn();

jest.mock("@/lib/api", () => ({
  api: { get: jest.fn() },
}));

jest.mock("react-router-dom", () => {
  const actual = jest.requireActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

jest.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ user: { is_premium: true } }),
}));

jest.mock("@/lib/i18n", () => ({
  useI18n: () => ({ t: (key) => key }),
}));

jest.mock("@/components/Navbar", () => () => <nav />);

jest.mock("@/components/TradingCard", () => ({
  CardFront: () => <div data-testid="card-front" />,
}));

jest.mock("@/components/LibraryCoverageReadiness", () => ({ onOpenReviews }) => (
  <button type="button" data-testid="coverage-reviews" onClick={() => onOpenReviews("class,feat", "manuale del giocatore.pdf")}>
    REVISIONI
  </button>
));

jest.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }) => <div {...props}>{children}</div>,
  },
}));

describe("Collection review routing", () => {
  let container;
  let root;

  beforeEach(() => {
    jest.clearAllMocks();
    api.get.mockResolvedValue({ data: [] });
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  it("opens the review queue with the selected categories and manual encoded in the URL", async () => {
    await act(async () => {
      root.render(<Collection />);
      await Promise.resolve();
    });

    await act(async () => {
      container.querySelector('[data-testid="coverage-reviews"]').click();
    });

    expect(mockNavigate).toHaveBeenCalledWith(
      "/revisioni?types=class%2Cfeat&source=manuale+del+giocatore.pdf",
    );
  });
});