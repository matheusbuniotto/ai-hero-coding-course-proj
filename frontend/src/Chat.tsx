import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "./api";
import type { AgentMessage, AgentSessionSummary, WorkspaceRole } from "./api";
import type { ChatWidth } from "./layout";
import { useActiveSession } from "./useActiveSession";
import { useAsync } from "./useAsync";

interface ChatProps {
  workspaceId: number;
  agentName: string | null;
  role: WorkspaceRole;
  width?: ChatWidth;
  onWidthChange?: (width: ChatWidth) => void;
  canHide?: boolean;
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
  onWidthChange,
  canHide = true,
}: ChatProps) {
  const sessions = useActiveSession(workspaceId, agentName);
  const session = sessions.session;
  const canSend = role !== "viewer" && session !== null && !isEnded(session);

  return (
    <aside className={`chat-column chat-${width}`} aria-label="Agent session">
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
          isViewer={role === "viewer"}
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
  isViewer,
}: {
  workspaceId: number;
  session: AgentSessionSummary;
  canSend: boolean;
  isViewer: boolean;
}) {
  const messages = useAsync<AgentMessage[]>(
    () => api.sessionMessages(workspaceId, session.id),
    [workspaceId, session.id],
  );
  const [localTurns, setLocalTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
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
      {canSend ? (
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
      ) : (
        !isEnded(session) &&
        isViewer && <p className="notice">Viewers cannot send messages.</p>
      )}
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
