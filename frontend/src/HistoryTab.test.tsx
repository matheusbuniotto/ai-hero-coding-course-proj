import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HistoryTab } from "./HistoryTab";

function fakeApi(bodies: Record<string, unknown>) {
  return vi.fn(async (url: string) => {
    const path = url.split("?")[0];
    return { ok: true, status: 200, json: async () => bodies[path] } as Response;
  });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("HistoryTab", () => {
  it("shows an empty state with nothing resolved yet", async () => {
    vi.stubGlobal("fetch", fakeApi({ "/workspace/history": [] }));
    render(<HistoryTab workspaceId={1} />);

    expect(await screen.findByText("No history yet")).toBeDefined();
  });

  it("lists resolved changes with their outcome", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "/workspace/history": [
          {
            id: 1,
            path: "notes.md",
            status: "approved",
            base_content: "old",
            proposed_content: "new",
            created_at: "2026-09-10T00:00:00Z",
            resolved_at: "2026-09-10T01:00:00Z",
          },
          {
            id: 2,
            path: "draft.md",
            status: "rejected",
            base_content: "x",
            proposed_content: "y",
            created_at: "2026-09-10T00:00:00Z",
            resolved_at: "2026-09-10T02:00:00Z",
          },
        ],
      }),
    );
    render(<HistoryTab workspaceId={1} />);

    expect(await screen.findByText("notes.md")).toBeDefined();
    expect(screen.getByText("approved")).toBeDefined();
    expect(screen.getByText("draft.md")).toBeDefined();
    expect(screen.getByText("rejected")).toBeDefined();
  });
});
