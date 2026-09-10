import { api } from "./api";
import type { AgentSessionSummary } from "./api";
import { useAsync } from "./useAsync";
import type { Async } from "./useAsync";

/** The session to resume for an agent: the live one, or else the most recent. */
export function useActiveSession(
  workspaceId: number,
  agentName: string | null,
): Async<AgentSessionSummary[]> & { session: AgentSessionSummary | null } {
  const sessions = useAsync<AgentSessionSummary[]>(
    () => (agentName ? api.listSessions(workspaceId, agentName) : Promise.resolve([])),
    [workspaceId, agentName],
  );
  const session = sessions.data?.find((s) => s.ended_at === null) ?? sessions.data?.[0] ?? null;
  return { ...sessions, session };
}
