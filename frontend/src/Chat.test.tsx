import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Chat } from "./Chat";

const LIVE_SESSION = {
  id: 1,
  workspace_id: 1,
  agent_name: "support",
  created_at: "2026-09-10T00:00:00Z",
  ended_at: null,
};

const ENDED_SESSION = { ...LIVE_SESSION, id: 2, ended_at: "2026-09-10T01:00:00Z" };

/** Routes a fake fetch by method + path, ignoring the query string. */
function fakeApi(handlers: Record<string, (init?: RequestInit) => unknown>) {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.split("?")[0];
    const method = init?.method ?? "GET";
    const handler = handlers[`${method} ${path}`];
    if (!handler) throw new Error(`no handler for ${method} ${path}`);
    const body = handler(init);
    if (body instanceof Error) {
      return {
        ok: false,
        status: 500,
        statusText: "error",
        json: async () => ({ detail: body.message }),
      } as Response;
    }
    return { ok: true, status: 200, json: async () => body } as Response;
  });
}

beforeEach(() => {
  vi.stubGlobal("location", { assign: vi.fn() });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Chat", () => {
  it("prompts to select an agent when none is chosen", () => {
    vi.stubGlobal("fetch", fakeApi({}));
    render(<Chat workspaceId={1} agentName={null} role="owner" />);

    expect(screen.getByText("Select an agent to start a session.")).toBeDefined();
  });

  it("offers to start a session when there is no live one", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({ "GET /workspace/agent/sessions": () => [] }),
    );
    render(<Chat workspaceId={1} agentName="support" role="owner" />);

    expect(
      await screen.findByText("No live session with support yet."),
    ).toBeDefined();
    expect(screen.getByRole("button", { name: "Start session" })).toBeDefined();
  });

  it("a viewer cannot start a session", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({ "GET /workspace/agent/sessions": () => [] }),
    );
    render(<Chat workspaceId={1} agentName="support" role="viewer" />);

    await screen.findByText("No live session with support yet.");
    expect(screen.queryByRole("button", { name: "Start session" })).toBeNull();
    expect(screen.getByText("Viewers cannot start a session.")).toBeDefined();
  });

  it("starts a session and resumes it once created", async () => {
    let started = false;
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "GET /workspace/agent/sessions": () => (started ? [LIVE_SESSION] : []),
        "POST /workspace/agent/sessions": () => {
          started = true;
          return LIVE_SESSION;
        },
        "GET /workspace/agent/sessions/1/messages": () => [],
      }),
    );
    render(<Chat workspaceId={1} agentName="support" role="owner" />);

    fireEvent.click(await screen.findByRole("button", { name: "Start session" }));

    expect(await screen.findByLabelText("Message")).toBeDefined();
  });

  it("shows the user's turn immediately and the agent's reply when it arrives", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "GET /workspace/agent/sessions": () => [LIVE_SESSION],
        "GET /workspace/agent/sessions/1/messages": () => [],
        "POST /workspace/agent/sessions/1/messages": () => ({
          id: 99,
          role: "assistant",
          content: "Ahoy!",
          created_at: "2026-09-10T00:00:01Z",
        }),
      }),
    );
    render(<Chat workspaceId={1} agentName="support" role="owner" />);

    fireEvent.change(await screen.findByLabelText("Message"), {
      target: { value: "hello there" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("hello there")).toBeDefined();
    expect(await screen.findByText("Ahoy!")).toBeDefined();
  });

  it("distinguishes tool/code activity from prose in the transcript", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "GET /workspace/agent/sessions": () => [LIVE_SESSION],
        "GET /workspace/agent/sessions/1/messages": () => [
          {
            id: 1,
            role: "assistant",
            content: "Sure, running it now.\n\n$ python greet.py\nexit code: 0\nstdout:\nahoy",
            created_at: "2026-09-10T00:00:01Z",
          },
        ],
      }),
    );
    render(<Chat workspaceId={1} agentName="support" role="owner" />);

    expect(await screen.findByText("Sure, running it now.")).toBeDefined();
    const activity = await screen.findByText(/\$ python greet\.py/);
    expect(activity.tagName).toBe("PRE");
    expect(activity.className).toBe("turn-tool-activity");
  });

  it("keeps the user's message and surfaces an error instead of losing it", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "GET /workspace/agent/sessions": () => [LIVE_SESSION],
        "GET /workspace/agent/sessions/1/messages": () => [],
        "POST /workspace/agent/sessions/1/messages": () => new Error("agent unavailable"),
      }),
    );
    render(<Chat workspaceId={1} agentName="support" role="owner" />);

    fireEvent.change(await screen.findByLabelText("Message"), {
      target: { value: "run the report" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("run the report")).toBeDefined();
    expect(await screen.findByText(/Failed to send: agent unavailable/)).toBeDefined();
  });

  it("an ended session is read-only, with no composer", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "GET /workspace/agent/sessions": () => [ENDED_SESSION],
        "GET /workspace/agent/sessions/2/messages": () => [
          { id: 1, role: "user", content: "hi", created_at: "2026-09-10T00:00:00Z" },
        ],
      }),
    );
    render(<Chat workspaceId={1} agentName="support" role="owner" />);

    expect(await screen.findByText(/This session has ended/)).toBeDefined();
    expect(screen.queryByLabelText("Message")).toBeNull();
  });

  it("a viewer sees the transcript of a live session but cannot send", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "GET /workspace/agent/sessions": () => [LIVE_SESSION],
        "GET /workspace/agent/sessions/1/messages": () => [],
      }),
    );
    render(<Chat workspaceId={1} agentName="support" role="viewer" />);

    await waitFor(() => expect(screen.queryByText("Loading…")).toBeNull());
    expect(screen.queryByLabelText("Message")).toBeNull();
    expect(screen.getByText("Viewers cannot send messages.")).toBeDefined();
  });
});
