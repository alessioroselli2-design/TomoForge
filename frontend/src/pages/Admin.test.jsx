import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";

import { api } from "@/lib/api";
import Admin from "./Admin";

global.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock("@/lib/api", () => ({
  api: { get: jest.fn(), post: jest.fn() },
}));

jest.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ user: { user_id: "admin-1", is_admin: true }, loading: false }),
}));

jest.mock("@/components/Navbar", () => () => <nav />);
jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));
jest.mock("framer-motion", () => ({
  motion: { div: ({ children }) => <div>{children}</div> },
}));

const users = [{ user_id: "owner-1", name: "Elminster", email: "elm@example.test", is_premium: false }];
const status = {
  owner_user_id: "owner-1",
  ruleset: "2014",
  total_groups: 12,
  pending_groups: 3,
  verified_groups: 5,
  conflict_groups: 2,
  low_confidence_groups: 1,
  excluded_records: 4,
  records_total: 28,
  canonical_total: 17,
};
const retryStatus = {
  owner_user_id: "owner-1",
  translatable_total: 10,
  translated_total: 10,
  failed_total: 0,
  processing_total: 0,
  pending_total: 0,
  translation_not_ready: 0,
  retryable_total: 0,
  blocked_total: 0,
  errors: {},
  ready_for_verification: true,
};
const translationStatus = {
  owner_user_id: "owner-1",
  translatable_total: 10,
  translated_total: 10,
  pending: 0,
  ai_verified: 8,
  conflict: 1,
  low_confidence: 0,
  failed: 0,
  stale: 0,
  human_verified: 0,
  translation_failed: 0,
  translation_processing: 0,
  translation_pending: 0,
  translation_not_ready: 0,
  verification_complete: 10,
  ready_for_canonicalization: true,
};

const settle = async () => {
  await new Promise((resolve) => setTimeout(resolve, 10));
  await Promise.resolve();
};

describe("Admin canonicalization", () => {
  let container;
  let root;

  beforeEach(() => {
    jest.clearAllMocks();
    api.get.mockImplementation((path) => {
      if (path === "/admin/users") return Promise.resolve({ data: users });
      if (path === "/admin/translation-retry/status") return Promise.resolve({ data: retryStatus });
      if (path === "/admin/translation-verification/status") return Promise.resolve({ data: translationStatus });
      if (path === "/admin/canonicalization/status") return Promise.resolve({ data: status });
      return Promise.resolve({ data: {} });
    });
    api.post.mockResolvedValue({ data: { ...status, processed_groups: 3 } });
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  it("renders the safe three-step flow and never starts a batch on mount", async () => {
    await act(async () => {
      root.render(<MemoryRouter><Admin /></MemoryRouter>);
      await settle();
    });

    expect(container.textContent).toContain("D&D 5e · Regole 2014");
    expect(container.textContent).toContain("Recupero traduzioni fallite");
    expect(container.textContent).toContain("Pronte per la verifica AI");
    expect(container.textContent).toContain("Verifica AI delle traduzioni");
    expect(container.textContent).toContain("Pronte per la fase 2");
    expect(container.textContent).toContain("Verificati");
    expect(container.textContent).toContain("5");
    expect(container.textContent).toContain("Conflitti");
    expect(container.textContent).toContain("Bassa confidenza");
    expect(container.textContent).toContain("restano bloccati");
    expect(container.textContent).toContain("senza imporre una revisione manuale");
    expect(api.get).toHaveBeenCalledWith("/admin/translation-retry/status", {
      params: { user_id: "owner-1" },
    });
    expect(api.get).toHaveBeenCalledWith("/admin/canonicalization/status", {
      params: { user_id: "owner-1" },
    });
    expect(api.get).toHaveBeenCalledWith("/admin/translation-verification/status", {
      params: { user_id: "owner-1" },
    });
    expect(api.post).not.toHaveBeenCalled();
  });

  it("submits the exact canonical batch payload and refreshes status after completion", async () => {
    await act(async () => {
      root.render(<MemoryRouter><Admin /></MemoryRouter>);
      await settle();
    });

    const input = container.querySelector('[data-testid="canonical-batch-size"]');
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
      setter.call(input, "8");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await act(async () => {
      container.querySelector('[data-testid="canonical-run"]').click();
      await settle();
    });

    expect(api.post).toHaveBeenCalledWith("/admin/canonicalization/run", {
      user_id: "owner-1",
      batch_size: 8,
      ruleset: "2014",
    });
    expect(api.get.mock.calls.filter(([path]) => path === "/admin/canonicalization/status")).toHaveLength(2);
  });

  it("runs a bounded failed-translation recovery batch before verification", async () => {
    const initialRetryStatus = {
      ...retryStatus,
      translated_total: 8,
      failed_total: 2,
      translation_not_ready: 2,
      retryable_total: 2,
      ready_for_verification: false,
    };
    api.get.mockImplementation((path) => {
      if (path === "/admin/users") return Promise.resolve({ data: users });
      if (path === "/admin/translation-retry/status") return Promise.resolve({ data: initialRetryStatus });
      if (path === "/admin/translation-verification/status") return Promise.resolve({ data: translationStatus });
      if (path === "/admin/canonicalization/status") return Promise.resolve({ data: status });
      return Promise.resolve({ data: {} });
    });
    api.post.mockResolvedValueOnce({
      data: {
        ...retryStatus,
        processed_records: 2,
        recovered_records: 2,
        still_failed_records: 0,
      },
    });

    await act(async () => {
      root.render(<MemoryRouter><Admin /></MemoryRouter>);
      await settle();
    });

    expect(container.querySelector('[data-testid="translation-run"]').disabled).toBe(true);
    const input = container.querySelector('[data-testid="retry-batch-size"]');
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
      setter.call(input, "2");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await act(async () => {
      container.querySelector('[data-testid="retry-run"]').click();
      await settle();
    });

    expect(api.post).toHaveBeenCalledWith("/admin/translation-retry/run", {
      user_id: "owner-1",
      batch_size: 2,
    });
    expect(container.querySelector('[data-testid="retry-status"]').textContent).toContain("Pronte per la verifica AI");
    expect(container.querySelector('[data-testid="translation-run"]').disabled).toBe(false);
    expect(api.get.mock.calls.filter(([path]) => path === "/admin/translation-verification/status")).toHaveLength(2);
  });

  it("runs a bounded translation-verification batch", async () => {
    api.post.mockResolvedValueOnce({ data: { ...translationStatus, ai_verified: 9 } });
    await act(async () => {
      root.render(<MemoryRouter><Admin /></MemoryRouter>);
      await settle();
    });

    const input = container.querySelector('[data-testid="translation-batch-size"]');
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
      setter.call(input, "7");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await act(async () => {
      container.querySelector('[data-testid="translation-run"]').click();
      await settle();
    });

    expect(api.post).toHaveBeenCalledWith("/admin/translation-verification/run", {
      user_id: "owner-1",
      batch_size: 7,
    });
    expect(container.querySelector('[data-testid="translation-status"]').textContent).toContain("9");
  });

  it("keeps verification and canonicalization disabled while translations are not ready", async () => {
    api.get.mockImplementation((path) => {
      if (path === "/admin/users") return Promise.resolve({ data: users });
      if (path === "/admin/translation-retry/status") {
        return Promise.resolve({
          data: {
            ...retryStatus,
            translated_total: 9,
            failed_total: 1,
            retryable_total: 1,
            translation_not_ready: 1,
            ready_for_verification: false,
          },
        });
      }
      if (path === "/admin/translation-verification/status") {
        return Promise.resolve({ data: { ...translationStatus, translation_failed: 1, translation_not_ready: 1, ready_for_canonicalization: false } });
      }
      if (path === "/admin/canonicalization/status") return Promise.resolve({ data: status });
      return Promise.resolve({ data: {} });
    });
    await act(async () => {
      root.render(<MemoryRouter><Admin /></MemoryRouter>);
      await settle();
    });

    expect(container.querySelector('[data-testid="translation-run"]').disabled).toBe(true);
    expect(container.querySelector('[data-testid="translation-retry-gate"]').textContent).toContain("Completa prima il recupero");
    expect(container.querySelector('[data-testid="canonical-run"]').disabled).toBe(true);
    expect(container.querySelector('[data-testid="canonical-translation-gate"]').textContent).toContain("Completa la fase 1");
  });
});
