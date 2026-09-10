import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MembersTab } from "./MembersTab";

const MEMBERS = [
  { user_id: 1, email: "owner@example.com", role: "owner" },
  { user_id: 2, email: "viewer@example.com", role: "viewer" },
];

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

describe("MembersTab", () => {
  it("lists members and their roles", async () => {
    vi.stubGlobal("fetch", fakeApi({ "GET /workspaces/1/members": () => MEMBERS }));
    render(<MembersTab workspaceId={1} role="owner" />);

    expect(await screen.findByText("owner@example.com")).toBeDefined();
    expect(screen.getByText("viewer@example.com")).toBeDefined();
  });

  it("hides invite and remove controls from a non-owner", async () => {
    vi.stubGlobal("fetch", fakeApi({ "GET /workspaces/1/members": () => MEMBERS }));
    render(<MembersTab workspaceId={1} role="editor" />);

    await screen.findByText("owner@example.com");
    expect(screen.queryByLabelText("Email")).toBeNull();
    expect(screen.queryByRole("button", { name: "Remove" })).toBeNull();
  });

  it("lets an owner invite a member", async () => {
    let invited = false;
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "GET /workspaces/1/members": () =>
          invited ? [...MEMBERS, { user_id: 3, email: "new@example.com", role: "viewer" }] : MEMBERS,
        "POST /workspaces/1/members": () => {
          invited = true;
          return { user_id: 3, email: "new@example.com", role: "viewer" };
        },
      }),
    );
    render(<MembersTab workspaceId={1} role="owner" />);
    await screen.findByText("owner@example.com");

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "new@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Invite" }));

    expect(await screen.findByText("new@example.com")).toBeDefined();
  });

  it("lets an owner remove a member", async () => {
    let removed = false;
    vi.stubGlobal(
      "fetch",
      fakeApi({
        "GET /workspaces/1/members": () => (removed ? [MEMBERS[0]] : MEMBERS),
        "DELETE /workspaces/1/members/2": () => {
          removed = true;
          return { removed_user_id: 2 };
        },
      }),
    );
    render(<MembersTab workspaceId={1} role="owner" />);
    await screen.findByText("viewer@example.com");

    fireEvent.click(screen.getAllByRole("button", { name: "Remove" })[1]);

    await waitFor(() => expect(screen.queryByText("viewer@example.com")).toBeNull());
  });
});
