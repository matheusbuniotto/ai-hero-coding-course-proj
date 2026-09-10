import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ReviewTab } from "./ReviewTab";

const PROPOSAL = {
  id: 1,
  path: "notes.md",
  status: "pending",
  base_content: "old",
  proposed_content: "new",
  created_at: "2026-09-10T00:00:00Z",
  resolved_at: null,
};

function fakeApi(handlers: Record<string, (init?: RequestInit) => unknown>) {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.split("?")[0];
    const method = init?.method ?? "GET";
    const handler = handlers[`${method} ${path}`];
    if (!handler) throw new Error(`no handler for ${method} ${path}`);
    const body = handler(init);
    if (body instanceof Error) {
      return { ok: false, status: 404, json: async () => ({ detail: body.message }) } as Response;
    }
    return { ok: true, status: 200, json: async () => body } as Response;
  });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("ReviewTab", () => {
  it("shows an empty state with nothing pending", async () => {
    vi.stubGlobal("fetch", fakeApi({ "GET /workspace/proposals": () => [] }));
    render(<ReviewTab workspaceId={1} role="owner" />);

    expect(await screen.findByText("Nothing to review")).toBeDefined();
  });

  it("lists a pending proposal with its diff", async () => {
    vi.stubGlobal("fetch", fakeApi({ "GET /workspace/proposals": () => [PROPOSAL] }));
    render(<ReviewTab workspaceId={1} role="owner" />);

    expect(await screen.findByText("notes.md")).toBeDefined();
    expect(screen.getByText("old")).toBeDefined();
    expect(screen.getByText("new")).toBeDefined();
  });

  it("lets an owner approve a proposal", async () => {
    let approved = false;
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "GET /workspace/proposals": () => (approved ? [] : [PROPOSAL]),
        "POST /workspace/proposals/1/approve": () => {
          approved = true;
          return { ...PROPOSAL, status: "approved" };
        },
      }),
    );
    render(<ReviewTab workspaceId={1} role="owner" />);

    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));

    expect(await screen.findByText("Nothing to review")).toBeDefined();
  });

  it("hides approve controls from an editor", async () => {
    vi.stubGlobal("fetch", fakeApi({ "GET /workspace/proposals": () => [PROPOSAL] }));
    render(<ReviewTab workspaceId={1} role="editor" />);

    await screen.findByText("notes.md");
    expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
  });

  it("surfaces an error resolving a proposal someone else already resolved", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "GET /workspace/proposals": () => [PROPOSAL],
        "POST /workspace/proposals/1/approve": () => new Error("No pending proposal 1"),
      }),
    );
    render(<ReviewTab workspaceId={1} role="owner" />);

    const entry = within(await screen.findByText("notes.md").then((el) => el.closest("li")!));
    fireEvent.click(entry.getByRole("button", { name: "Approve" }));

    expect(await screen.findByText(/No pending proposal 1/)).toBeDefined();
  });
});
