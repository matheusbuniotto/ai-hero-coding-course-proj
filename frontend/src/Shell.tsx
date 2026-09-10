import { NavLink, useNavigate, useSearchParams } from "react-router-dom";

import { api } from "./api";
import type { FileContent, Me, WorkspaceDetail } from "./api";
import { Chat } from "./Chat";
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

export function Shell({ me, workspaceId, view, reloadMe }: ShellProps) {
  const workspace = useAsync(() => api.workspace(workspaceId), [workspaceId]);
  const pending = useAsync(() => api.pendingProposals(workspaceId), [workspaceId]);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const openPath = searchParams.get(FILE_PARAM);
  const activeAgent = searchParams.get(AGENT_PARAM);

  const pendingPaths = new Set((pending.data ?? []).map((p) => p.path));

  function openFile(path: string) {
    navigate(`/w/${workspaceId}/library?${FILE_PARAM}=${encodeURIComponent(path)}`);
  }

  function closeFile() {
    const next = new URLSearchParams(searchParams);
    next.delete(FILE_PARAM);
    setSearchParams(next);
  }

  function selectAgent(name: string) {
    const next = new URLSearchParams(searchParams);
    next.set(AGENT_PARAM, name);
    setSearchParams(next);
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
        <div className="body">
          <Sidebar
            workspace={workspace.data}
            activePath={view === "library" ? openPath : null}
            activeAgent={activeAgent}
            pendingPaths={pendingPaths}
            onSelectFile={openFile}
            onSelectAgent={selectAgent}
          />
          <main className="main">
            <ViewPanel
              view={view}
              workspace={workspace.data}
              workspaceId={workspaceId}
              openPath={openPath}
              pendingPaths={pendingPaths}
              onCloseFile={closeFile}
            />
          </main>
          <Chat
            workspaceId={workspaceId}
            agentName={activeAgent}
            role={workspace.data?.role ?? "viewer"}
          />
        </div>
      )}
    </div>
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
}

function ViewPanel({
  view,
  workspace,
  workspaceId,
  openPath,
  pendingPaths,
  onCloseFile,
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
      />
    );
  }

  const label = VIEWS.find((v) => v.slug === view)!.label;
  return (
    <section>
      <h1>{label}</h1>
      <p className="notice">{label} is not built yet.</p>
    </section>
  );
}

function Library({
  workspace,
  workspaceId,
  openPath,
  pendingPaths,
  onCloseFile,
}: {
  workspace: WorkspaceDetail;
  workspaceId: number;
  openPath: string | null;
  pendingPaths: ReadonlySet<string>;
  onCloseFile: () => void;
}) {
  if (openPath) {
    return (
      <FileTab
        workspaceId={workspaceId}
        path={openPath}
        inReview={pendingPaths.has(openPath)}
        onClose={onCloseFile}
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
    </section>
  );
}

function FileTab({
  workspaceId,
  path,
  inReview,
  onClose,
}: {
  workspaceId: number;
  path: string;
  inReview: boolean;
  onClose: () => void;
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
        <button type="button" className="file-tab-close" aria-label={`Close ${path}`} onClick={onClose}>
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
