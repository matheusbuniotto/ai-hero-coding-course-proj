import { NavLink } from "react-router-dom";

import { api } from "./api";
import type { Me, WorkspaceDetail } from "./api";
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

export function Shell({ me, workspaceId, view, reloadMe }: ShellProps) {
  const workspace = useAsync(() => api.workspace(workspaceId), [workspaceId]);
  const pending = useAsync(() => api.pendingProposals(workspaceId), [workspaceId]);

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
          <Sidebar workspace={workspace.data} />
          <main className="main">
            <ViewPanel view={view} workspace={workspace.data} />
          </main>
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

function ViewPanel({ view, workspace }: { view: View; workspace: WorkspaceDetail | null }) {
  if (!workspace) return <p className="notice">Loading…</p>;
  if (view === "library") return <Library workspace={workspace} />;

  const label = VIEWS.find((v) => v.slug === view)!.label;
  return (
    <section>
      <h1>{label}</h1>
      <p className="notice">{label} is not built yet.</p>
    </section>
  );
}

function Library({ workspace }: { workspace: WorkspaceDetail }) {
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
