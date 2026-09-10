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

export interface Proposal {
  id: number;
  path: string;
  status: "pending" | "approved" | "rejected" | "superseded";
}

export interface FileContent {
  path: string;
  content: string;
}

export type AgentMessageRole = "user" | "assistant";

export interface AgentSessionSummary {
  id: number;
  workspace_id: number;
  agent_name: string;
  created_at: string;
  ended_at: string | null;
}

export interface AgentMessage {
  id: number;
  role: AgentMessageRole;
  content: string;
  created_at: string;
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
    request<Proposal[]>(`/workspace/proposals?workspace_id=${workspaceId}`),

  fileContent: (workspaceId: number, path: string) =>
    request<FileContent>(
      `/workspace/files?workspace_id=${workspaceId}&path=${encodeURIComponent(path)}`,
    ),

  createWorkspace: (name: string) => post<WorkspaceSummary>("/workspaces", { name }),

  forkWorkspace: (workspaceId: number, name: string) =>
    post<WorkspaceSummary>(`/workspaces/${workspaceId}/fork`, { name }),

  listSessions: (workspaceId: number, agentName: string) =>
    request<AgentSessionSummary[]>(
      `/workspace/agent/sessions?workspace_id=${workspaceId}&agent_name=${encodeURIComponent(agentName)}`,
    ),

  startSession: (workspaceId: number, agentName: string) =>
    post<AgentSessionSummary>(`/workspace/agent/sessions?workspace_id=${workspaceId}`, {
      agent_name: agentName,
    }),

  sessionMessages: (workspaceId: number, sessionId: number) =>
    request<AgentMessage[]>(
      `/workspace/agent/sessions/${sessionId}/messages?workspace_id=${workspaceId}`,
    ),

  sendMessage: (workspaceId: number, sessionId: number, message: string) =>
    post<AgentMessage>(
      `/workspace/agent/sessions/${sessionId}/messages?workspace_id=${workspaceId}`,
      { message },
    ),
};
