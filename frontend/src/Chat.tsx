import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "./api";
import type { AgentMessage, AgentSessionSummary, SessionProposal, WorkspaceRole } from "./api";
import type { ChatWidth } from "./layout";
import { DiffView } from "./DiffView";
import { useAction } from "./useAction";
import { useActiveSession } from "./useActiveSession";
import { useAsync } from "./useAsync";

interface ChatProps {
  workspaceId: number;
  agentName: string | null;
  role: WorkspaceRole;
  width?: ChatWidth;
  widthPx?: number;
  onWidthChange?: (width: ChatWidth) => void;
  canHide?: boolean;
  onProposalsChanged?: () => void;
}

/** A turn already confirmed by the server, or one still in flight / failed locally. */
type Turn =
  | { kind: "message"; id: number | string; role: "user" | "assistant"; content: string }
  | { kind: "pending"; id: string; content: string }
  | { kind: "error"; id: string; content: string; detail: string };

export function Chat({
  workspaceId,
  agentName,
  role,
  width = "normal",
  widthPx,
  onWidthChange,
  canHide = true,
  onProposalsChanged,
}: ChatProps) {
  const sessions = useActiveSession(workspaceId, agentName);
  const session = sessions.session;
  const canSend = role !== "viewer" && session !== null && !isEnded(session);

  return (
    <aside
      className={`chat-column chat-${width}`}
      style={widthPx ? { width: widthPx } : undefined}
      aria-label="Agent session"
    >
      {onWidthChange && (
        <div className="chat-controls">
          <button
            type="button"
            className="chat-widen"
            aria-label={width === "wide" ? "Narrow chat" : "Widen chat"}
            onClick={() => onWidthChange(width === "wide" ? "normal" : "wide")}
          >
            {width === "wide" ? "⇤" : "⇥"}
          </button>
          <button
            type="button"
            className="chat-hide"
            aria-label="Hide chat"
            onClick={() => onWidthChange("hidden")}
            disabled={!canHide}
            title={canHide ? undefined : "At least one pane must stay open"}
          >
            ×
          </button>
        </div>
      )}
      {!agentName ? (
        <p className="notice">Select an agent to start a session.</p>
      ) : sessions.error ? (
        <p className="notice error">{sessions.error}</p>
      ) : !sessions.data ? (
        <p className="notice">Loading…</p>
      ) : session ? (
        <Transcript
          key={session.id}
          workspaceId={workspaceId}
          session={session}
          canSend={canSend}
          role={role}
          onEnded={sessions.reload}
          onProposalsChanged={onProposalsChanged}
        />
      ) : (
        <StartSession
          agentName={agentName}
          canStart={role !== "viewer"}
          onStart={async () => {
            await api.startSession(workspaceId, agentName);
            sessions.reload();
          }}
        />
      )}
    </aside>
  );
}

function StartSession({
  agentName,
  canStart,
  onStart,
}: {
  agentName: string;
  canStart: boolean;
  onStart: () => Promise<void>;
}) {
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setStarting(true);
    setError(null);
    try {
      await onStart();
    } catch (cause) {
      setError(String(cause));
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="chat-empty">
      <p className="notice">No live session with {agentName} yet.</p>
      {canStart ? (
        <button type="button" onClick={handleClick} disabled={starting}>
          {starting ? "Starting…" : "Start session"}
        </button>
      ) : (
        <p className="notice">Viewers cannot start a session.</p>
      )}
      {error && <p className="notice error">{error}</p>}
    </div>
  );
}

function Transcript({
  workspaceId,
  session,
  canSend,
  role,
  onEnded,
  onProposalsChanged,
}: {
  workspaceId: number;
  session: AgentSessionSummary;
  canSend: boolean;
  role: WorkspaceRole;
  onEnded: () => void;
  onProposalsChanged?: () => void;
}) {
  const isViewer = role === "viewer";
  const messages = useAsync<AgentMessage[]>(
    () => api.sessionMessages(workspaceId, session.id),
    [workspaceId, session.id],
  );
  const [localTurns, setLocalTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const endSession = useAction(async () => {
    await api.submitSessionProposal(workspaceId, session.id);
    onEnded();
  });
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLocalTurns([]);
  }, [session.id]);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  });

  const serverTurns: Turn[] = (messages.data ?? []).map((m) => ({
    kind: "message",
    id: m.id,
    role: m.role,
    content: m.content,
  }));
  const turns = [...serverTurns, ...localTurns];

  async function send() {
    const content = text.trim();
    if (!content || sending) return;
    const localId = `pending-${Date.now()}`;
    setText("");
    setSending(true);
    setLocalTurns((prev) => [...prev, { kind: "pending", id: localId, content }]);
    try {
      const reply = await api.sendMessage(workspaceId, session.id, content);
      setLocalTurns((prev) => [
        ...prev.filter((t) => t.id !== localId),
        { kind: "message", id: `${localId}-user`, role: "user", content },
        { kind: "message", id: reply.id, role: "assistant", content: reply.content },
      ]);
    } catch (cause) {
      const detail = cause instanceof ApiError ? cause.message : String(cause);
      setLocalTurns((prev) => [
        ...prev.filter((t) => t.id !== localId),
        { kind: "message", id: `${localId}-user`, role: "user", content },
        { kind: "error", id: `${localId}-error`, content, detail },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="chat-transcript">
      {isEnded(session) && (
        <p className="chat-ended notice">
          This session has ended — read-only. Its changes went to review.
        </p>
      )}
      {messages.error && <p className="notice error">{messages.error}</p>}
      <div className="chat-log" ref={listRef}>
        {turns.length === 0 && !messages.error ? (
          <p className="notice">No messages yet — say hello.</p>
        ) : (
          turns.map((turn) => <TurnView key={`${turn.kind}-${turn.id}`} turn={turn} />)
        )}
      </div>
      {isEnded(session) ? (
        <SessionProposalCard
          workspaceId={workspaceId}
          session={session}
          role={role}
          onProposalsChanged={onProposalsChanged}
        />
      ) : canSend ? (
        <>
          <form
            className="chat-composer"
            onSubmit={(e) => {
              e.preventDefault();
              void send();
            }}
          >
            <textarea
              aria-label="Message"
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send();
                }
              }}
              disabled={sending}
            />
            <button type="submit" disabled={sending || !text.trim()}>
              {sending ? "Sending…" : "Send"}
            </button>
          </form>
          <div className="chat-end">
            <button type="button" onClick={() => void endSession.run()} disabled={endSession.busy}>
              {endSession.busy ? "Ending…" : "End session"}
            </button>
            {endSession.error && <p className="notice error">{endSession.error}</p>}
          </div>
        </>
      ) : (
        isViewer && <p className="notice">Viewers cannot send messages.</p>
      )}
    </div>
  );
}

function SessionProposalCard({
  workspaceId,
  session,
  role,
  onProposalsChanged,
}: {
  workspaceId: number;
  session: AgentSessionSummary;
  role: WorkspaceRole;
  onProposalsChanged?: () => void;
}) {
  const proposal = useAsync<SessionProposal>(
    () => api.sessionProposal(workspaceId, session.id),
    [workspaceId, session.id],
  );
  const canApprove = role === "owner";
  const approve = useAction(async () => {
    await api.approveSessionProposal(workspaceId, session.id);
    proposal.reload();
    onProposalsChanged?.();
  });
  const reject = useAction(async () => {
    await api.rejectSessionProposal(workspaceId, session.id);
    proposal.reload();
    onProposalsChanged?.();
  });
  const busy = approve.busy || reject.busy;
  const error = approve.error ?? reject.error;

  if (proposal.error) return <p className="notice error">{proposal.error}</p>;
  if (!proposal.data) return <p className="notice">Loading…</p>;

  const changes = proposal.data.changes;
  const allResolved = changes.length > 0 && changes.every((c) => c.status !== "pending");
  // All-or-nothing only holds while every file is still untouched; a file resolved
  // some other way (e.g. singly, from the Review tab) makes the session mixed.
  const mixed = !allResolved && changes.some((c) => c.status !== "pending");

  return (
    <div className="session-proposal-card">
      <p className="session-proposal-title">Save this session?</p>
      {changes.length === 0 ? (
        <p className="notice">Nothing changed in this session.</p>
      ) : (
        <ul className="session-proposal-files">
          {changes.map((change) => (
            <li key={change.proposal_id}>
              <div className="session-proposal-file-bar">
                <span>{change.path}</span>
                {change.status !== "pending" && (
                  <span className={`history-entry-status history-status-${change.status}`}>
                    {change.status}
                  </span>
                )}
              </div>
              <DiffView base={change.base_content} proposed={change.proposed_content} />
            </li>
          ))}
        </ul>
      )}
      {error && <p className="notice error">{error}</p>}
      {changes.length > 0 &&
        (allResolved ? (
          <p className="notice">This session's changes have all been resolved.</p>
        ) : mixed ? (
          <p className="notice">
            Part of this session was already resolved elsewhere — approve or discard the rest
            from the Review tab.
          </p>
        ) : canApprove ? (
          <div className="session-proposal-actions">
            <button type="button" onClick={() => void approve.run()} disabled={busy}>
              Approve
            </button>
            <button type="button" onClick={() => void reject.run()} disabled={busy}>
              Discard
            </button>
          </div>
        ) : (
          <p className="notice">Waiting for an owner to review.</p>
        ))}
    </div>
  );
}

function isEnded(session: AgentSessionSummary): boolean {
  return session.ended_at !== null;
}

function TurnView({ turn }: { turn: Turn }) {
  if (turn.kind === "error") {
    return (
      <div className="turn turn-user">
        <span className="turn-role">You</span>
        <p>{turn.content}</p>
        <p className="turn-error">Failed to send: {turn.detail}</p>
      </div>
    );
  }
  if (turn.kind === "pending") {
    return (
      <div className="turn turn-user turn-pending">
        <span className="turn-role">You</span>
        <p>{turn.content}</p>
      </div>
    );
  }

  const sections = turn.content.split("\n\n");
  return (
    <div className={`turn turn-${turn.role}`}>
      <span className="turn-role">{turn.role === "user" ? "You" : "Agent"}</span>
      {sections.map((section, i) =>
        section.startsWith("$ ") ? (
          <pre key={i} className="turn-tool-activity">
            {section}
          </pre>
        ) : (
          <p key={i}>{section}</p>
        ),
      )}
    </div>
  );
}
