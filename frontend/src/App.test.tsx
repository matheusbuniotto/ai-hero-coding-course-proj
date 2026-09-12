import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { LOGIN_URL } from "./api";

const ME = {
  user: { id: 1, email: "walker@example.com" },
  workspaces: [
    { id: 1, name: "walker's workspace", kind: "personal", role: "owner" },
    { id: 2, name: "Team Wiki", kind: "team", role: "editor" },
  ],
};

const WORKSPACE = {
  ...ME.workspaces[0],
  agents: ["writer"],
  tree: ["agents/writer/prompt.md", "notes.md"],
};

const EMPTY_WORKSPACE = { ...ME.workspaces[1], agents: [], tree: [] };

/** A stand-in API: every path answers 200 with its canned body, unless overridden. */
function fakeApi(bodies: Record<string, unknown>, status = 200) {
  return vi.fn(async (url: string) => {
    const path = url.split("?")[0];
    return {
      ok: status === 200,
      status,
      statusText: "error",
      json: async () => (status === 200 ? bodies[path] : { detail: "nope" }),
    } as Response;
  });
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", fakeApi({ "/me": ME, "/workspace/api": WORKSPACE }));
  vi.stubGlobal("location", { assign: vi.fn() });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("the workspace shell", () => {
  it("shows the signed-in email, the current workspace and the role", async () => {
    renderAt("/w/1/library");
    const topbar = within(await screen.findByRole("banner"));

    expect(await topbar.findByText("walker@example.com")).toBeDefined();
    expect(await topbar.findByText(/walker's workspace/, { selector: ".workspace-name" }))
      .toBeDefined();
    expect(await topbar.findByText("owner")).toBeDefined();
  });

  it("offers all four top-level views", async () => {
    renderAt("/w/1/library");

    for (const label of ["Library", "Review", "History", "Members"]) {
      expect(await screen.findByRole("link", { name: label })).toBeDefined();
    }
  });

  it("renders the view named by the URL, so a reload lands in the same place", async () => {
    renderAt("/w/1/history");

    expect(await screen.findByRole("heading", { name: "History" })).toBeDefined();
  });

  it("lists the workspace's agents and files in the sidebar", async () => {
    renderAt("/w/1/library");

    const agents = within(await screen.findByRole("list", { name: "Agents" }));
    const files = within(await screen.findByRole("list", { name: "Files" }));

    expect(agents.getByText("writer")).toBeDefined();
    expect(files.getByText("prompt.md")).toBeDefined();
    expect(files.getByText("notes.md")).toBeDefined();
  });

  it("offers an empty state rather than a blank sidebar", async () => {
    vi.stubGlobal("fetch", fakeApi({ "/me": ME, "/workspace/api": EMPTY_WORKSPACE }));

    renderAt("/w/2/library");

    expect(await screen.findByText("No agents yet")).toBeDefined();
    expect(await screen.findByText("No files yet")).toBeDefined();
  });

  it("badges Review with the workspace's pending proposal count", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({ "/me": ME, "/workspace/api": WORKSPACE, "/workspace/proposals": [{}, {}] }),
    );

    renderAt("/w/1/library");

    const review = await screen.findByRole("link", { name: /Review/ });
    expect(await within(review).findByText("2")).toBeDefined();
  });

  it("keeps the linked workspace when the URL names a view that does not exist", async () => {
    renderAt("/w/2/nonsense");

    expect(await screen.findByRole("link", { name: "Library" })).toHaveProperty(
      "pathname",
      "/w/2/library",
    );
  });

  it("lets the user switch to another workspace they belong to", async () => {
    renderAt("/w/1/library");
    fireEvent.click(await screen.findByRole("button", { name: /walker's workspace/ }));
    const list = within(screen.getByRole("list", { name: "Workspaces" }));

    const names = list
      .getAllByRole("button")
      .map((item) => item.querySelector(".switcher-item-name")?.textContent);
    expect(names).toEqual(["walker's workspace", "Team Wiki"]);

    // Picking one closes the menu.
    fireEvent.click(list.getByRole("button", { name: /Team Wiki/ }));
    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: "Switch workspace" })).toBeNull(),
    );
  });

  it("creates a team workspace from the name the user typed", async () => {
    const created = { id: 3, name: "New Team", kind: "team", role: "owner" };
    const fetch = fakeApi({ "/me": ME, "/workspace/api": WORKSPACE, "/workspaces": created });
    vi.stubGlobal("fetch", fetch);
    renderAt("/w/1/library");

    fireEvent.click(await screen.findByRole("button", { name: /walker's workspace/ }));
    fireEvent.change(screen.getByLabelText("New workspace name"), {
      target: { value: "New Team" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create team" }));

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        "/workspaces",
        expect.objectContaining({ method: "POST", body: JSON.stringify({ name: "New Team" }) }),
      ),
    );
    // ...and the shell moves to the workspace it just made, without unmounting first.
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith("/workspace/api?workspace_id=3", expect.anything()),
    );
  });

  it("forks the current workspace under a new name", async () => {
    const fork = { id: 4, name: "My Fork", kind: "team", role: "owner" };
    const fetch = fakeApi({ "/me": ME, "/workspace/api": WORKSPACE, "/workspaces/1/fork": fork });
    vi.stubGlobal("fetch", fetch);
    renderAt("/w/1/library");

    fireEvent.click(await screen.findByRole("button", { name: /walker's workspace/ }));
    fireEvent.change(screen.getByLabelText("New workspace name"), {
      target: { value: "My Fork" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Fork this" }));

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        "/workspaces/1/fork",
        expect.objectContaining({ method: "POST", body: JSON.stringify({ name: "My Fork" }) }),
      ),
    );
  });

  it("sends an unauthenticated user to the magic-link login page", async () => {
    vi.stubGlobal("fetch", fakeApi({}, 401));

    renderAt("/");

    await waitFor(() => expect(window.location.assign).toHaveBeenCalledWith(LOGIN_URL));
    expect(screen.queryByText(/Error/)).toBeNull();
  });
});

describe("the projects home", () => {
  it("lists the projects the user has access to, as cards", async () => {
    renderAt("/");

    expect(await screen.findByRole("button", { name: /walker's workspace/ })).toBeDefined();
    expect(await screen.findByRole("button", { name: /Team Wiki/ })).toBeDefined();
  });

  it("filters projects by kind", async () => {
    renderAt("/");
    await screen.findByRole("button", { name: /Team Wiki/ });

    fireEvent.click(screen.getByRole("button", { name: "Team" }));

    expect(screen.getByRole("button", { name: /Team Wiki/ })).toBeDefined();
    expect(screen.queryByRole("button", { name: /walker's workspace/ })).toBeNull();
  });

  it("opens a workspace when its card is clicked", async () => {
    renderAt("/");
    fireEvent.click(await screen.findByRole("button", { name: /walker's workspace/ }));

    const topbar = within(await screen.findByRole("banner"));
    expect(await topbar.findByText(/walker's workspace/, { selector: ".workspace-name" }))
      .toBeDefined();
  });

  it("offers starter templates, clearly marked as not built yet", async () => {
    renderAt("/");

    const template = await screen.findByRole("button", { name: /Blank project/ });
    expect(within(template).getByText("Coming soon")).toBeDefined();

    fireEvent.click(template);
    expect(await screen.findByText(/templates are coming soon/)).toBeDefined();
  });

  it("gets back to the projects home from inside a workspace", async () => {
    renderAt("/w/1/library");

    fireEvent.click(await screen.findByRole("link", { name: "All projects" }));

    expect(await screen.findByRole("button", { name: /Team Wiki/ })).toBeDefined();
  });
});

describe("reading a file in the library", () => {
  const FILE = { path: "notes.md", content: "# Notes\n\nHello there." };

  it("opens a file from the sidebar and renders its canonical content", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({ "/me": ME, "/workspace/api": WORKSPACE, "/workspace/files": FILE }),
    );
    renderAt("/w/1/library");

    fireEvent.click(await screen.findByRole("button", { name: /notes\.md/ }));

    expect(await screen.findByText(/# Notes/)).toBeDefined();
    expect(screen.getByText(/Hello there\./)).toBeDefined();
  });

  it("shows the open file in a closable tab, and closing it leaves the shell intact", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({ "/me": ME, "/workspace/api": WORKSPACE, "/workspace/files": FILE }),
    );
    renderAt("/w/1/library");
    fireEvent.click(await screen.findByRole("button", { name: /notes\.md/ }));
    await screen.findByText(/# Notes/);

    fireEvent.click(screen.getByRole("button", { name: "Close notes.md" }));

    expect(screen.queryByText(/# Notes/)).toBeNull();
    // The shell and sidebar are still there, ready to open another file.
    expect(await screen.findByRole("button", { name: /notes\.md/ })).toBeDefined();
    expect(screen.getByRole("list", { name: "Agents" })).toBeDefined();
  });

  it("keeps the open file across a reload, via the URL", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({ "/me": ME, "/workspace/api": WORKSPACE, "/workspace/files": FILE }),
    );

    renderAt("/w/1/library?file=notes.md");

    expect(await screen.findByText(/# Notes/)).toBeDefined();
  });

  it("marks a file with a pending proposal as having a change in review", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "/me": ME,
        "/workspace/api": WORKSPACE,
        "/workspace/proposals": [{ id: 1, path: "notes.md", status: "pending" }],
      }),
    );

    renderAt("/w/1/library");

    const notesLink = await screen.findByRole("button", { name: /notes\.md/ });
    expect(within(notesLink).getByText("in review")).toBeDefined();
  });

  it("refuses to render a file the caller may not read", async () => {
    vi.stubGlobal(
      "fetch",
      fakeApi({ "/me": ME, "/workspace/api": WORKSPACE, "/workspace/files": FILE }, 403),
    );

    renderAt("/w/1/library?file=notes.md");

    expect(await screen.findByText(/nope/)).toBeDefined();
    expect(screen.queryByText(/# Notes/)).toBeNull();
  });

  it("lets a viewer open and read a file", async () => {
    const viewerMe = {
      ...ME,
      workspaces: [{ ...WORKSPACE, role: "viewer" }],
    };
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "/me": viewerMe,
        "/workspace/api": { ...WORKSPACE, role: "viewer" },
        "/workspace/files": FILE,
      }),
    );

    renderAt("/w/1/library");
    fireEvent.click(await screen.findByRole("button", { name: /notes\.md/ }));

    expect(await screen.findByText(/# Notes/)).toBeDefined();
  });
});

describe("pane layout", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "/me": ME,
        "/workspace/api": WORKSPACE,
        "/workspace/agent/sessions": [],
      }),
    );
  });

  it("opens the sandbox output panel from its own control, and closes it again", async () => {
    renderAt("/w/1/library");

    fireEvent.click(await screen.findByRole("button", { name: "Show sandbox output" }));
    expect(await screen.findByRole("region", { name: "Sandbox output" })).toBeDefined();

    fireEvent.click(screen.getByRole("button", { name: "Close sandbox output" }));
    expect(screen.queryByRole("region", { name: "Sandbox output" })).toBeNull();
  });

  it("lists a closed pane in the status bar and reopens it from there", async () => {
    renderAt("/w/1/library");
    const statusbar = within(await screen.findByRole("contentinfo", { name: "Closed panes" }));

    // The output panel starts closed, so the status bar already offers a way to it.
    expect(await statusbar.findByText("Show Sandbox output")).toBeDefined();
    fireEvent.click(statusbar.getByText("Show Sandbox output"));

    expect(await screen.findByRole("region", { name: "Sandbox output" })).toBeDefined();
    expect(statusbar.queryByText("Show Sandbox output")).toBeNull();
  });

  it("refuses to close the chat once it is the only visible pane", async () => {
    renderAt("/w/1/library");

    fireEvent.click(await screen.findByRole("button", { name: "Hide chat" }));

    // Chat and its hide control are still there — the close was a no-op.
    expect(await screen.findByRole("complementary", { name: "Agent session" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Hide chat" })).toHaveProperty("disabled", true);
  });

  it("widens the chat and then restores it", async () => {
    renderAt("/w/1/library");

    const widen = await screen.findByRole("button", { name: "Widen chat" });
    fireEvent.click(widen);
    expect(await screen.findByRole("complementary", { name: "Agent session" })).toHaveProperty(
      "className",
      "chat-column chat-wide",
    );

    fireEvent.click(screen.getByRole("button", { name: "Narrow chat" }));
    expect(await screen.findByRole("complementary", { name: "Agent session" })).toHaveProperty(
      "className",
      "chat-column chat-normal",
    );
  });

  it("survives a reload by keeping pane state in the URL", async () => {
    renderAt("/w/1/library?output=1&chat=wide");

    expect(await screen.findByRole("region", { name: "Sandbox output" })).toBeDefined();
    expect(await screen.findByRole("complementary", { name: "Agent session" })).toHaveProperty(
      "className",
      "chat-column chat-wide",
    );
  });
});
