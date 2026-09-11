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

export type ProposalStatus = "pending" | "approved" | "rejected" | "superseded";

export interface Proposal {
  id: number;
  path: string;
  status: ProposalStatus;
  base_content: string | null;
  proposed_content: string;
  created_at: string;
  resolved_at: string | null;
}

export interface Member {
  user_id: number;
  email: string;
  role: WorkspaceRole;
}

export interface SessionProposalChange {
  proposal_id: number;
  path: string;
  status: ProposalStatus;
  base_content: string | null;
  proposed_content: string;
}

export interface SessionProposal {
  session_id: number;
  ended_at: string | null;
  changes: SessionProposalChange[];
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

export type CodeExecutionStatus = "succeeded" | "failed" | "errored";

export interface CodeExecution {
  id: number;
  command: string;
  status: CodeExecutionStatus;
  exit_code: number | null;
  stdout: string;
  stderr: string;
  produced: string[];
  duration_ms: number;
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

const del = <T>(path: string): Promise<T> => request<T>(path, { method: "DELETE" });

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

  listExecutions: (workspaceId: number, sessionId: number) =>
    request<CodeExecution[]>(
      `/workspace/agent/sessions/${sessionId}/executions?workspace_id=${workspaceId}`,
    ),

  history: (workspaceId: number) =>
    request<Proposal[]>(`/workspace/history?workspace_id=${workspaceId}`),

  proposeFile: (workspaceId: number, path: string, content: string) =>
    post<Proposal>(`/workspace/files/propose?workspace_id=${workspaceId}`, { path, content }),

  approveProposal: (workspaceId: number, proposalId: number) =>
    post<Proposal>(`/workspace/proposals/${proposalId}/approve?workspace_id=${workspaceId}`, {}),

  rejectProposal: (workspaceId: number, proposalId: number) =>
    post<Proposal>(`/workspace/proposals/${proposalId}/reject?workspace_id=${workspaceId}`, {}),

  members: (workspaceId: number) =>
    request<Member[]>(`/workspaces/${workspaceId}/members`),

  inviteMember: (workspaceId: number, email: string, role: WorkspaceRole) =>
    post<Member>(`/workspaces/${workspaceId}/members`, { email, role }),

  removeMember: (workspaceId: number, userId: number) =>
    del<{ removed_user_id: number }>(`/workspaces/${workspaceId}/members/${userId}`),

  sessionProposal: (workspaceId: number, sessionId: number) =>
    request<SessionProposal>(
      `/workspace/agent/sessions/${sessionId}/proposal?workspace_id=${workspaceId}`,
    ),

  submitSessionProposal: (workspaceId: number, sessionId: number) =>
    post<SessionProposal>(
      `/workspace/agent/sessions/${sessionId}/proposal?workspace_id=${workspaceId}`,
      {},
    ),

  approveSessionProposal: (workspaceId: number, sessionId: number) =>
    post<SessionProposal>(
      `/workspace/agent/sessions/${sessionId}/proposal/approve?workspace_id=${workspaceId}`,
      {},
    ),

  rejectSessionProposal: (workspaceId: number, sessionId: number) =>
    post<SessionProposal>(
      `/workspace/agent/sessions/${sessionId}/proposal/reject?workspace_id=${workspaceId}`,
      {},
    ),
};
