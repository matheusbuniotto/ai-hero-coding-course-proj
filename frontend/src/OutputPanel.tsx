import { useEffect } from "react";

import { api } from "./api";
import type { CodeExecution } from "./api";
import { useActiveSession } from "./useActiveSession";
import { useAsync } from "./useAsync";

interface OutputPanelProps {
  workspaceId: number;
  agentName: string | null;
  onClose: () => void;
  canClose: boolean;
  heightPx?: number;
}

/** How long a session stays open before the panel stops polling for new runs. */
const POLL_MS = 3000;

export function OutputPanel({ workspaceId, agentName, onClose, canClose, heightPx }: OutputPanelProps) {
  const { session } = useActiveSession(workspaceId, agentName);
  const live = session !== null && session.ended_at === null;

  const executions = useAsync<CodeExecution[]>(
    () => (session ? api.listExecutions(workspaceId, session.id) : Promise.resolve([])),
    [workspaceId, session?.id],
  );

  useEffect(() => {
    if (!live) return;
    const timer = setInterval(() => executions.reload(), POLL_MS);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [live, session?.id]);

  return (
    <section
      className="output-panel"
      style={heightPx ? { height: heightPx, flex: "0 0 auto" } : undefined}
      aria-label="Sandbox output"
    >
      <div className="output-panel-bar">
        <span className="output-panel-title">Sandbox output</span>
        <button
          type="button"
          className="pane-close"
          aria-label="Close sandbox output"
          onClick={onClose}
          disabled={!canClose}
          title={canClose ? undefined : "At least one pane must stay open"}
        >
          ×
        </button>
      </div>
      <div className="output-panel-body">
        {!agentName ? (
          <p className="notice">Select an agent to see its sandbox output.</p>
        ) : executions.error ? (
          <p className="notice error">{executions.error}</p>
        ) : !session ? (
          <p className="notice">No session yet.</p>
        ) : !executions.data ? (
          <p className="notice">Loading…</p>
        ) : executions.data.length === 0 ? (
          <p className="notice">No commands run in this session yet.</p>
        ) : (
          <ul className="execution-list">
            {executions.data.map((execution) => (
              <ExecutionEntry key={execution.id} execution={execution} />
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function ExecutionEntry({ execution }: { execution: CodeExecution }) {
  const failed = execution.status !== "succeeded";
  return (
    <li className={`execution-entry execution-${execution.status}`}>
      <div className="execution-summary">
        <span className={`execution-status ${failed ? "execution-status-failed" : ""}`}>
          {execution.status}
        </span>
        <code className="execution-command">{execution.command}</code>
        <span className="execution-meta">
          {execution.exit_code !== null && <span>exit {execution.exit_code}</span>}
          <span>{formatDuration(execution.duration_ms)}</span>
        </span>
      </div>
      {execution.stdout && (
        <pre className="execution-stream execution-stdout">{execution.stdout}</pre>
      )}
      {execution.stderr && (
        <pre className="execution-stream execution-stderr">{execution.stderr}</pre>
      )}
    </li>
  );
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
