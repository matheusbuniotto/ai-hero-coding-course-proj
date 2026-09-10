import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "./api";
import type { Me, WorkspaceSummary } from "./api";
import type { View } from "./views";

interface SwitcherProps {
  me: Me;
  workspaceId: number;
  view: View;
  onWorkspacesChanged: () => void;
}

export function WorkspaceSwitcher({ me, workspaceId, view, onWorkspacesChanged }: SwitcherProps) {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const go = (id: number) => navigate(`/w/${id}/${view}`);

  const add = (create: () => Promise<WorkspaceSummary>) => async () => {
    setError(null);
    try {
      const workspace = await create();
      setName("");
      go(workspace.id);
      onWorkspacesChanged();
    } catch (cause) {
      setError(String(cause));
    }
  };

  return (
    <div className="switcher">
      <label>
        Workspace
        <select value={workspaceId} onChange={(event) => go(Number(event.target.value))}>
          {me.workspaces.map((workspace) => (
            <option key={workspace.id} value={workspace.id}>
              {workspace.name}
            </option>
          ))}
        </select>
      </label>

      <input
        aria-label="New workspace name"
        placeholder="New workspace name"
        value={name}
        onChange={(event) => setName(event.target.value)}
      />
      <button disabled={!name.trim()} onClick={add(() => api.createWorkspace(name.trim()))}>
        Create team
      </button>
      <button
        disabled={!name.trim()}
        onClick={add(() => api.forkWorkspace(workspaceId, name.trim()))}
      >
        Fork this
      </button>

      {error && <span className="error">{error}</span>}
    </div>
  );
}
