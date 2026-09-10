import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { OutputPanel } from "./OutputPanel";

const LIVE_SESSION = {
  id: 1,
  workspace_id: 1,
  agent_name: "support",
  created_at: "2026-09-10T00:00:00Z",
  ended_at: null,
};

const ENDED_SESSION = { ...LIVE_SESSION, id: 2, ended_at: "2026-09-10T01:00:00Z" };

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

beforeEach(() => {
  vi.stubGlobal("location", { assign: vi.fn() });
});

describe("OutputPanel", () => {
  it("prompts to select an agent when none is chosen", () => {
    vi.stubGlobal("fetch", fakeApi({}));
    render(<OutputPanel workspaceId={1} agentName={null} onClose={() => {}} canClose={true} />);

    expect(screen.getByText("Select an agent to see its sandbox output.")).toBeDefined();
  });

  it("says there is nothing yet when the session has run no commands", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "GET /workspace/agent/sessions": () => [ENDED_SESSION],
        "GET /workspace/agent/sessions/2/executions": () => [],
      }),
    );
    render(
      <OutputPanel workspaceId={1} agentName="support" onClose={() => {}} canClose={true} />,
    );

    expect(await screen.findByText("No commands run in this session yet.")).toBeDefined();
  });

  it("lists every command with its exit code, duration, stdout and stderr", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "GET /workspace/agent/sessions": () => [ENDED_SESSION],
        "GET /workspace/agent/sessions/2/executions": () => [
          {
            id: 1,
            command: "python greet.py",
            status: "succeeded",
            exit_code: 0,
            stdout: "ahoy\n",
            stderr: "",
            produced: [],
            duration_ms: 128,
            created_at: "2026-09-10T00:00:00Z",
          },
        ],
      }),
    );
    render(
      <OutputPanel workspaceId={1} agentName="support" onClose={() => {}} canClose={true} />,
    );

    expect(await screen.findByText("python greet.py")).toBeDefined();
    expect(screen.getByText("exit 0")).toBeDefined();
    expect(screen.getByText("128ms")).toBeDefined();
    expect(screen.getByText(/ahoy/)).toBeDefined();
  });

  it("makes a failed run visually distinct from a successful one", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "GET /workspace/agent/sessions": () => [ENDED_SESSION],
        "GET /workspace/agent/sessions/2/executions": () => [
          {
            id: 1,
            command: "python ok.py",
            status: "succeeded",
            exit_code: 0,
            stdout: "",
            stderr: "",
            produced: [],
            duration_ms: 10,
            created_at: "2026-09-10T00:00:00Z",
          },
          {
            id: 2,
            command: "python broken.py",
            status: "failed",
            exit_code: 1,
            stdout: "",
            stderr: "boom\n",
            produced: [],
            duration_ms: 20,
            created_at: "2026-09-10T00:00:01Z",
          },
        ],
      }),
    );
    render(
      <OutputPanel workspaceId={1} agentName="support" onClose={() => {}} canClose={true} />,
    );

    const ok = (await screen.findByText("python ok.py")).closest("li");
    const broken = screen.getByText("python broken.py").closest("li");

    expect(ok?.className).toContain("execution-succeeded");
    expect(broken?.className).toContain("execution-failed");
    expect(broken?.className).not.toBe(ok?.className);
  });

  it("disables its close control when it is the only pane left", () => {
    vi.stubGlobal("fetch", fakeApi({}));
    render(
      <OutputPanel workspaceId={1} agentName={null} onClose={() => {}} canClose={false} />,
    );

    expect(screen.getByRole("button", { name: "Close sandbox output" })).toHaveProperty(
      "disabled",
      true,
    );
  });
});
