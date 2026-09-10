import { api } from "./api";
import type { Proposal } from "./api";
import { useAsync } from "./useAsync";

export function HistoryTab({ workspaceId }: { workspaceId: number }) {
  const history = useAsync<Proposal[]>(() => api.history(workspaceId), [workspaceId]);
  const chronological = [...(history.data ?? [])].sort((a, b) =>
    (b.resolved_at ?? "").localeCompare(a.resolved_at ?? ""),
  );

  return (
    <section>
      <h1>History</h1>
      {history.error ? (
        <p className="notice error">{history.error}</p>
      ) : !history.data ? (
        <p className="notice">Loading…</p>
      ) : chronological.length === 0 ? (
        <p className="notice">No approved or rejected changes yet.</p>
      ) : (
        <ul className="history-list">
          {chronological.map((proposal) => (
            <li key={proposal.id} className={`history-entry history-${proposal.status}`}>
              <span className="history-entry-path">{proposal.path}</span>
              <span className={`history-entry-status history-status-${proposal.status}`}>
                {proposal.status}
              </span>
              <span className="history-entry-when">
                {proposal.resolved_at && new Date(proposal.resolved_at).toLocaleString()}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
