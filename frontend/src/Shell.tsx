import { useEffect, useState } from "react";
import { NavLink, useNavigate, useSearchParams } from "react-router-dom";

import { api } from "./api";
import type { FileContent, Me, WorkspaceDetail } from "./api";
import { Chat } from "./Chat";
import { HistoryTab } from "./HistoryTab";
import { canClose, closedPanes, PANE_LABELS } from "./layout";
import type { ChatWidth, PaneState } from "./layout";
import { MembersTab } from "./MembersTab";
import { OutputPanel } from "./OutputPanel";
import { ReviewTab } from "./ReviewTab";
import { Sidebar } from "./Sidebar";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";
import { VIEWS } from "./views";
import type { View } from "./views";
import { useAsync } from "./useAsync";

interface ShellProps {
  me: Me;
  workspaceId: number;
  view: View;
  reloadMe: () => void;
}

const FILE_PARAM = "file";
const AGENT_PARAM = "agent";
const OUTPUT_PARAM = "output";
const CHAT_PARAM = "chat";

export function Shell({ me, workspaceId, view, reloadMe }: ShellProps) {
  const workspace = useAsync(() => api.workspace(workspaceId), [workspaceId]);
  const pending = useAsync(() => api.pendingProposals(workspaceId), [workspaceId]);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const openPath = searchParams.get(FILE_PARAM);
  const activeAgent = searchParams.get(AGENT_PARAM);
  const outputOpen = searchParams.get(OUTPUT_PARAM) === "1";
  const chatWidth = asChatWidth(searchParams.get(CHAT_PARAM));
  const [lastFilePath, setLastFilePath] = useState<string | null>(null);

  useEffect(() => {
    if (openPath) setLastFilePath(openPath);
  }, [openPath]);

  const pendingPaths = new Set((pending.data ?? []).map((p) => p.path));
  const paneState: PaneState = { fileOpen: openPath !== null, outputOpen, chatWidth };

  function openFile(path: string) {
    navigate(`/w/${workspaceId}/library?${FILE_PARAM}=${encodeURIComponent(path)}`);
  }

  function closeFile() {
    if (!canClose(paneState, "file")) return;
    const next = new URLSearchParams(searchParams);
    next.delete(FILE_PARAM);
    setSearchParams(next);
  }

  function selectAgent(name: string) {
    const next = new URLSearchParams(searchParams);
    next.set(AGENT_PARAM, name);
    setSearchParams(next);
  }

  function openOutput() {
    const next = new URLSearchParams(searchParams);
    next.set(OUTPUT_PARAM, "1");
    setSearchParams(next);
  }

  function closeOutput() {
    if (!canClose(paneState, "output")) return;
    const next = new URLSearchParams(searchParams);
    next.delete(OUTPUT_PARAM);
    setSearchParams(next);
  }

  function setChatWidth(width: ChatWidth) {
    if (width === "hidden" && !canClose(paneState, "chat")) return;
    const next = new URLSearchParams(searchParams);
    if (width === "normal") next.delete(CHAT_PARAM);
    else next.set(CHAT_PARAM, width);
    setSearchParams(next);
  }

  function reopen(pane: "file" | "output" | "chat") {
    if (pane === "output") openOutput();
    else if (pane === "chat") setChatWidth("normal");
    else if (lastFilePath) openFile(lastFilePath);
  }

  return (
    <div className="shell">
      <header className="topbar">
        <WorkspaceSwitcher
          me={me}
          workspaceId={workspaceId}
          view={view}
          onWorkspacesChanged={reloadMe}
        />
        <Identity workspace={workspace.data} email={me.user.email} />
      </header>

      <nav className="tabs">
        {VIEWS.map(({ slug, label }) => (
          <NavLink key={slug} to={`/w/${workspaceId}/${slug}`} className="tab">
            {label}
            {slug === "review" && pending.data && pending.data.length > 0 && (
              <span className="badge">{pending.data.length}</span>
            )}
          </NavLink>
        ))}
      </nav>

      {workspace.error ? (
        <p className="notice">{workspace.error}</p>
      ) : (
        <>
          <div className="body">
            <Sidebar
              workspace={workspace.data}
              activePath={view === "library" ? openPath : null}
              activeAgent={activeAgent}
              pendingPaths={pendingPaths}
              onSelectFile={openFile}
              onSelectAgent={selectAgent}
            />
            <div className="workspace-panes">
              <main className="main">
                <ViewPanel
                  view={view}
                  workspace={workspace.data}
                  workspaceId={workspaceId}
                  openPath={openPath}
                  pendingPaths={pendingPaths}
                  onCloseFile={closeFile}
                  canCloseFile={canClose(paneState, "file")}
                  outputOpen={outputOpen}
                  onOpenOutput={openOutput}
                  onProposalsChanged={pending.reload}
                />
              </main>
              {outputOpen && (
                <OutputPanel
                  workspaceId={workspaceId}
                  agentName={activeAgent}
                  onClose={closeOutput}
                  canClose={canClose(paneState, "output")}
                />
              )}
            </div>
            {chatWidth !== "hidden" && (
              <Chat
                workspaceId={workspaceId}
                agentName={activeAgent}
                role={workspace.data?.role ?? "viewer"}
                width={chatWidth}
                onWidthChange={setChatWidth}
                canHide={canClose(paneState, "chat")}
                onProposalsChanged={pending.reload}
              />
            )}
          </div>
          <StatusBar paneState={paneState} onReopen={reopen} canReopenFile={lastFilePath !== null} />
        </>
      )}
    </div>
  );
}

function asChatWidth(value: string | null): ChatWidth {
  return value === "wide" || value === "hidden" ? value : "normal";
}

function StatusBar({
  paneState,
  onReopen,
  canReopenFile,
}: {
  paneState: PaneState;
  onReopen: (pane: "file" | "output" | "chat") => void;
  canReopenFile: boolean;
}) {
  // A file that was never opened isn't a "closed pane" with something to reopen.
  const closed = closedPanes(paneState).filter((pane) => pane !== "file" || canReopenFile);
  return (
    <footer className="statusbar" aria-label="Closed panes">
      {closed.length === 0 ? (
        <span className="statusbar-empty">All panes open</span>
      ) : (
        closed.map((pane) => (
          <button
            key={pane}
            type="button"
            className="statusbar-item"
            onClick={() => onReopen(pane)}
          >
            Show {PANE_LABELS[pane]}
          </button>
        ))
      )}
    </footer>
  );
}

function Identity({ workspace, email }: { workspace: WorkspaceDetail | null; email: string }) {
  return (
    <div className="identity">
      {workspace && (
        <span className="workspace-name">
          {workspace.name} <span className="role">{workspace.role}</span>
        </span>
      )}
      <span className="email">{email}</span>
    </div>
  );
}

interface ViewPanelProps {
  view: View;
  workspace: WorkspaceDetail | null;
  workspaceId: number;
  openPath: string | null;
  pendingPaths: ReadonlySet<string>;
  onCloseFile: () => void;
  canCloseFile: boolean;
  outputOpen: boolean;
  onOpenOutput: () => void;
  onProposalsChanged: () => void;
}

function ViewPanel({
  view,
  workspace,
  workspaceId,
  openPath,
  pendingPaths,
  onCloseFile,
  canCloseFile,
  outputOpen,
  onOpenOutput,
  onProposalsChanged,
}: ViewPanelProps) {
  if (!workspace) return <p className="notice">Loading…</p>;
  if (view === "library") {
    return (
      <Library
        workspace={workspace}
        workspaceId={workspaceId}
        openPath={openPath}
        pendingPaths={pendingPaths}
        onCloseFile={onCloseFile}
        canCloseFile={canCloseFile}
        outputOpen={outputOpen}
        onOpenOutput={onOpenOutput}
      />
    );
  }
  if (view === "review") {
    return (
      <ReviewTab workspaceId={workspaceId} role={workspace.role} onResolved={onProposalsChanged} />
    );
  }
  if (view === "history") {
    return <HistoryTab workspaceId={workspaceId} />;
  }
  if (view === "members") {
    return <MembersTab workspaceId={workspaceId} role={workspace.role} />;
  }
  return view satisfies never;
}

function Library({
  workspace,
  workspaceId,
  openPath,
  pendingPaths,
  onCloseFile,
  canCloseFile,
  outputOpen,
  onOpenOutput,
}: {
  workspace: WorkspaceDetail;
  workspaceId: number;
  openPath: string | null;
  pendingPaths: ReadonlySet<string>;
  onCloseFile: () => void;
  canCloseFile: boolean;
  outputOpen: boolean;
  onOpenOutput: () => void;
}) {
  if (openPath) {
    return (
      <FileTab
        workspaceId={workspaceId}
        path={openPath}
        inReview={pendingPaths.has(openPath)}
        onClose={onCloseFile}
        canClose={canCloseFile}
      />
    );
  }

  return (
    <section>
      <h1>{workspace.name}</h1>
      {workspace.tree.length === 0 ? (
        <p className="notice">
          This workspace is empty. Start a session with an agent to propose its first files.
        </p>
      ) : (
        <p className="notice">
          {workspace.agents.length} agent(s) and {workspace.tree.length} file(s), listed in the
          sidebar.
        </p>
      )}
      {!outputOpen && (
        <button type="button" className="show-output" onClick={onOpenOutput}>
          Show sandbox output
        </button>
      )}
    </section>
  );
}

function FileTab({
  workspaceId,
  path,
  inReview,
  onClose,
  canClose,
}: {
  workspaceId: number;
  path: string;
  inReview: boolean;
  onClose: () => void;
  canClose: boolean;
}) {
  const file = useAsync<FileContent>(() => api.fileContent(workspaceId, path), [
    workspaceId,
    path,
  ]);

  return (
    <div className="file-tab">
      <div className="file-tab-bar">
        <span className="file-tab-title">
          <span>{path}</span>
          {inReview && (
            <span className="in-review" title="Change in review">
              in review
            </span>
          )}
        </span>
        <button
          type="button"
          className="file-tab-close"
          aria-label={`Close ${path}`}
          onClick={onClose}
          disabled={!canClose}
          title={canClose ? undefined : "At least one pane must stay open"}
        >
          ×
        </button>
      </div>
      {file.error ? (
        <p className="notice">{file.error}</p>
      ) : file.data ? (
        <pre className="document">{file.data.content}</pre>
      ) : (
        <p className="notice">Loading…</p>
      )}
    </div>
  );
}
