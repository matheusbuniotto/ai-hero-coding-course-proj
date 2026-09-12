import { Navigate, Route, Routes, useParams } from "react-router-dom";

import { api } from "./api";
import type { Me } from "./api";
import { ProjectsHome } from "./ProjectsHome";
import { Shell } from "./Shell";
import { VIEWS, isView } from "./views";
import { useAsync } from "./useAsync";

export function App() {
  const me = useAsync(() => api.me(), []);

  if (me.error) return <p className="notice">{me.error}</p>;
  if (!me.data) return <p className="notice">Loading…</p>;
  if (me.data.workspaces.length === 0) {
    return <p className="notice">You are not a member of any workspace yet.</p>;
  }

  return (
    <Routes>
      <Route path="/" element={<ProjectsHome me={me.data} />} />
      <Route path="/w/:workspaceId" element={<Navigate to={VIEWS[0].slug} replace />} />
      <Route
        path="/w/:workspaceId/:view"
        element={<WorkspaceRoute me={me.data} reloadMe={me.reload} />}
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function WorkspaceRoute({ me, reloadMe }: { me: Me; reloadMe: () => void }) {
  const { workspaceId, view } = useParams();
  const id = Number(workspaceId);

  if (!Number.isInteger(id)) return <Navigate to="/" replace />;
  // An unrecognised view still names a workspace the user meant to open.
  if (!isView(view)) return <Navigate to={`/w/${id}/${VIEWS[0].slug}`} replace />;
  return <Shell key={id} me={me} workspaceId={id} view={view} reloadMe={reloadMe} />;
}
