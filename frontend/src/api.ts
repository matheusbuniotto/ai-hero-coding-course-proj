export type WorkspaceRole = "owner" | "editor" | "viewer";
export type WorkspaceKind = "personal" | "team";

export interface WorkspaceSummary {
  id: number;
  name: string;
  kind: WorkspaceKind;
  role: WorkspaceRole;
}

export interface Me {
  user: { id: number; email: string };
  workspaces: WorkspaceSummary[];
}

export interface WorkspaceDetail extends WorkspaceSummary {
  agents: string[];
  tree: string[];
}

export const LOGIN_URL = "/auth/login";

/** Thrown when the API answers 401; the caller has already been sent to the login page. */
export class NotSignedIn extends Error {}

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: init?.body ? { "Content-Type": "application/json" } : undefined,
  });

  if (response.status === 401) {
    window.location.assign(LOGIN_URL);
    throw new NotSignedIn("Not signed in");
  }
  if (!response.ok) {
    throw new ApiError(await detail(response));
  }
  return (await response.json()) as T;
}

async function detail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
}

const post = <T>(path: string, body: unknown): Promise<T> =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  me: () => request<Me>("/me"),

  workspace: (workspaceId: number) =>
    request<WorkspaceDetail>(`/workspace/api?workspace_id=${workspaceId}`),

  pendingProposals: (workspaceId: number) =>
    request<unknown[]>(`/workspace/proposals?workspace_id=${workspaceId}`),

  createWorkspace: (name: string) => post<WorkspaceSummary>("/workspaces", { name }),

  forkWorkspace: (workspaceId: number, name: string) =>
    post<WorkspaceSummary>(`/workspaces/${workspaceId}/fork`, { name }),
};
