import { useEffect, useRef, useState } from "react";
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
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  const current = me.workspaces.find((workspace) => workspace.id === workspaceId);

  // The menu closes on Escape or a click anywhere outside it.
  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const go = (id: number) => {
    setOpen(false);
    navigate(`/w/${id}/${view}`);
  };

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
    <div className="switcher" ref={rootRef}>
      <button
        type="button"
        className="switcher-trigger"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <span className="switcher-avatar" aria-hidden="true">
          {(current?.name ?? "?").charAt(0).toUpperCase()}
        </span>
        <span className="workspace-name">{current?.name ?? "Workspace"}</span>
        {current && <span className="role">{current.role}</span>}
        <span className="switcher-chevron" aria-hidden="true" />
      </button>

      {open && (
        <div className="switcher-menu" role="dialog" aria-label="Switch workspace">
          <p className="switcher-eyebrow">Switch workspace</p>
          <ul className="switcher-list" aria-label="Workspaces">
            {me.workspaces.map((workspace) => (
              <li key={workspace.id}>
                <button
                  type="button"
                  className={`switcher-item${workspace.id === workspaceId ? " active" : ""}`}
                  aria-current={workspace.id === workspaceId ? "true" : undefined}
                  onClick={() => go(workspace.id)}
                >
                  <span className="switcher-avatar" aria-hidden="true">
                    {workspace.name.charAt(0).toUpperCase()}
                  </span>
                  <span className="switcher-item-text">
                    <span className="switcher-item-name">{workspace.name}</span>
                    <span className="switcher-item-meta">
                      {workspace.kind} · {workspace.role}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>

          <div className="switcher-new">
            <p className="switcher-eyebrow">New workspace</p>
            <input
              aria-label="New workspace name"
              placeholder="Name"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
            <div className="switcher-new-actions">
              <button
                type="button"
                className="switcher-create"
                disabled={!name.trim()}
                onClick={add(() => api.createWorkspace(name.trim()))}
              >
                Create team
              </button>
              <button
                type="button"
                disabled={!name.trim()}
                onClick={add(() => api.forkWorkspace(workspaceId, name.trim()))}
              >
                Fork this
              </button>
            </div>
            {error && <p className="error">{error}</p>}
          </div>
        </div>
      )}
    </div>
  );
}
