import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NewFileForm } from "./NewFileForm";

function fakeApi(handlers: Record<string, (init?: RequestInit) => unknown>) {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.split("?")[0];
    const method = init?.method ?? "GET";
    const handler = handlers[`${method} ${path}`];
    if (!handler) throw new Error(`no handler for ${method} ${path}`);
    return { ok: true, status: 200, json: async () => handler(init) } as Response;
  });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("NewFileForm", () => {
  it("proposes a new file and notifies its caller", async () => {
    let proposedBody: unknown = null;
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "POST /workspace/files/propose": (init) => {
          proposedBody = JSON.parse(init?.body as string);
          return {
            id: 1,
            path: "notes/todo.md",
            status: "pending",
            base_content: null,
            proposed_content: "buy milk",
            created_at: "2026-09-10T00:00:00Z",
            resolved_at: null,
          };
        },
      }),
    );
    const onCreated = vi.fn();
    render(<NewFileForm workspaceId={1} onCreated={onCreated} />);

    fireEvent.change(screen.getByLabelText("Path"), { target: { value: "notes/todo.md" } });
    fireEvent.change(screen.getByLabelText("Content"), { target: { value: "buy milk" } });
    fireEvent.click(screen.getByRole("button", { name: "Propose new file" }));

    await waitFor(() => expect(onCreated).toHaveBeenCalledTimes(1));
    expect(proposedBody).toEqual({ path: "notes/todo.md", content: "buy milk" });
    expect((screen.getByLabelText("Path") as HTMLInputElement).value).toBe("");
  });

  it("disables submit until a path is entered", () => {
    render(<NewFileForm workspaceId={1} onCreated={vi.fn()} />);

    expect((screen.getByRole("button", { name: "Propose new file" }) as HTMLButtonElement).disabled).toBe(
      true,
    );
    fireEvent.change(screen.getByLabelText("Path"), { target: { value: "a.md" } });
    expect((screen.getByRole("button", { name: "Propose new file" }) as HTMLButtonElement).disabled).toBe(
      false,
    );
  });

  it("surfaces an API error without losing the draft", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          ({ ok: false, status: 400, json: async () => ({ detail: "bad path" }) }) as Response,
      ),
    );
    render(<NewFileForm workspaceId={1} onCreated={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Path"), { target: { value: "bad" } });
    fireEvent.click(screen.getByRole("button", { name: "Propose new file" }));

    expect(await screen.findByText("bad path")).toBeDefined();
    expect((screen.getByLabelText("Path") as HTMLInputElement).value).toBe("bad");
  });
});
