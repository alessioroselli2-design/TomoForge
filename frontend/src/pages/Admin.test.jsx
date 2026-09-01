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

  it("renders canonical status and never starts a batch on mount", async () => {
    await act(async () => {
      root.render(<MemoryRouter><Admin /></MemoryRouter>);
      await settle();
    });

    expect(container.textContent).toContain("D&D 5e · Regole 2014");
    expect(container.textContent).toContain("Verificati");
    expect(container.textContent).toContain("5");
    expect(container.textContent).toContain("Conflitti");
    expect(container.textContent).toContain("Bassa confidenza");
    expect(container.textContent).toContain("restano bloccati");
    expect(container.textContent).toContain("senza imporre una revisione manuale");
    expect(api.get).toHaveBeenCalledWith("/admin/canonicalization/status", {
      params: { user_id: "owner-1" },
    });
    expect(api.post).not.toHaveBeenCalled();
  });

  it("submits the exact batch payload and refreshes status after completion", async () => {
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
});