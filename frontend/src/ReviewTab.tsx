import { api } from "./api";
import type { Proposal, WorkspaceRole } from "./api";
import { DiffView } from "./DiffView";
import { EmptyState } from "./EmptyState";
import { Loading } from "./Loading";
import { useAction } from "./useAction";
import { useAsync } from "./useAsync";

interface ReviewTabProps {
  workspaceId: number;
  role: WorkspaceRole;
  onResolved?: () => void;
}

export function ReviewTab({ workspaceId, role, onResolved }: ReviewTabProps) {
  const pending = useAsync<Proposal[]>(() => api.pendingProposals(workspaceId), [workspaceId]);
  const canApprove = role === "owner";

  return (
    <section>
      <h1>Review</h1>
      {pending.error ? (
        <p className="notice error">{pending.error}</p>
      ) : !pending.data ? (
        <Loading label="Loading proposals" lines={3} className="loading-cards" />
      ) : pending.data.length === 0 ? (
        <EmptyState
          icon="✅"
          title="Nothing to review"
          hint="Proposals an agent opens will show up here for approval."
        />
      ) : (
        <ul className="proposal-list">
          {pending.data.map((proposal) => (
            <ProposalEntry
              key={proposal.id}
              workspaceId={workspaceId}
              proposal={proposal}
              canApprove={canApprove}
              onResolved={() => {
                pending.reload();
                onResolved?.();
              }}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

function ProposalEntry({
  workspaceId,
  proposal,
  canApprove,
  onResolved,
}: {
  workspaceId: number;
  proposal: Proposal;
  canApprove: boolean;
  onResolved: () => void;
}) {
  const approve = useAction(async () => {
    await api.approveProposal(workspaceId, proposal.id);
    onResolved();
  });
  const reject = useAction(async () => {
    await api.rejectProposal(workspaceId, proposal.id);
    onResolved();
  });
  const busy = approve.busy || reject.busy;

  return (
    <li className="proposal-entry">
      <DiffView
        path={proposal.path}
        base={proposal.base_content}
        proposed={proposal.proposed_content}
        headerActions={
          canApprove ? (
            <div className="proposal-entry-actions">
              <button type="button" onClick={() => approve.run()} disabled={busy}>
                Approve
              </button>
              <button type="button" onClick={() => reject.run()} disabled={busy}>
                Reject
              </button>
            </div>
          ) : undefined
        }
      />
      {(approve.error ?? reject.error) && (
        <p className="notice error">{approve.error ?? reject.error}</p>
      )}
    </li>
  );
}
