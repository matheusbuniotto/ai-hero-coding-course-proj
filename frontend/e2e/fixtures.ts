import { test as base, expect } from "@playwright/test";
import type { APIRequestContext } from "@playwright/test";

export interface Seeded {
  email: string;
  personalId: number;
  teamId: number;
}

let counter = 0;

function uniqueEmail(): string {
  counter += 1;
  return `e2e-${Date.now()}-${process.pid}-${counter}@example.com`;
}

/**
 * Dev-login through the Vite proxy with the page's own request context, so the
 * httponly session cookie lands in the browser context the page uses.
 */
export async function devLogin(request: APIRequestContext, email: string): Promise<void> {
  const response = await request.post("/auth/dev-login", {
    form: { email },
    maxRedirects: 0,
  });
  expect(response.status(), "dev-login should redirect (is ICM_DEV_AUTH=1?)").toBe(303);
}

async function json<T>(request: APIRequestContext, method: "get" | "post", url: string, data?: unknown): Promise<T> {
  const response = method === "get" ? await request.get(url) : await request.post(url, { data });
  expect(response.ok(), `${method.toUpperCase()} ${url} -> ${response.status()}`).toBeTruthy();
  return (await response.json()) as T;
}

async function proposeAndApprove(request: APIRequestContext, workspaceId: number, path: string, content: string) {
  const proposal = await json<{ id: number }>(request, "post", `/workspace/files/propose?workspace_id=${workspaceId}`, {
    path,
    content,
  });
  await json(request, "post", `/workspace/proposals/${proposal.id}/approve?workspace_id=${workspaceId}`);
}

/**
 * A fresh user with a personal workspace holding an agent, a couple of files,
 * approved history and one pending proposal, plus a team workspace with a second member.
 */
async function seed(request: APIRequestContext): Promise<Seeded> {
  const email = uniqueEmail();
  await devLogin(request, email);

  const me = await json<{ workspaces: { id: number; kind: string }[] }>(request, "get", "/me");
  const personalId = me.workspaces.find((w) => w.kind === "personal")!.id;

  await proposeAndApprove(request, personalId, "agents/writer/prompt.md", "# Writer\n\nYou write docs.\n");
  await proposeAndApprove(request, personalId, "docs/intro.md", "# Intro\n\nHello world.\n");
  await json(request, "post", `/workspace/files/propose?workspace_id=${personalId}`, {
    path: "docs/intro.md",
    content: "# Intro\n\nHello, e2e world.\nA second line.\n",
  });

  const team = await json<{ id: number }>(request, "post", "/workspaces", { name: "E2E Team" });
  await json(request, "post", `/workspaces/${team.id}/members`, { email: `mate-${email}`, role: "editor" });

  return { email, personalId, teamId: team.id };
}

export const test = base.extend<{ seeded: Seeded }>({
  seeded: async ({ page }, use) => {
    await use(await seed(page.request));
  },
});

export { expect };
