import type { WorkspaceDetail } from "./api";
import { buildTree } from "./fileTree";
import type { TreeNode } from "./fileTree";

interface SidebarProps {
  workspace: WorkspaceDetail | null;
  activePath?: string | null;
  pendingPaths: ReadonlySet<string>;
  onSelectFile: (path: string) => void;
}

export function Sidebar({ workspace, activePath, pendingPaths, onSelectFile }: SidebarProps) {
  if (!workspace) return <aside className="sidebar" aria-busy="true" />;

  return (
    <aside className="sidebar">
      <h2>Agents</h2>
      {workspace.agents.length === 0 ? (
        <p className="empty">No agents yet</p>
      ) : (
        <ul className="agents" aria-label="Agents">
          {workspace.agents.map((name) => (
            <li key={name}>{name}</li>
          ))}
        </ul>
      )}

      <h2>Files</h2>
      {workspace.tree.length === 0 ? (
        <p className="empty">No files yet</p>
      ) : (
        <Nodes
          nodes={buildTree(workspace.tree)}
          label="Files"
          activePath={activePath}
          pendingPaths={pendingPaths}
          onSelectFile={onSelectFile}
        />
      )}
    </aside>
  );
}

function Nodes({
  nodes,
  label,
  activePath,
  pendingPaths,
  onSelectFile,
}: {
  nodes: TreeNode[];
  label?: string;
  activePath?: string | null;
  pendingPaths: ReadonlySet<string>;
  onSelectFile: (path: string) => void;
}) {
  return (
    <ul className="tree" aria-label={label}>
      {nodes.map((node) => (
        <li key={node.path} className={node.kind}>
          {node.kind === "folder" ? (
            <>
              {node.name}
              <Nodes
                nodes={node.children}
                activePath={activePath}
                pendingPaths={pendingPaths}
                onSelectFile={onSelectFile}
              />
            </>
          ) : (
            <button
              type="button"
              className={`file-link${node.path === activePath ? " active" : ""}`}
              onClick={() => onSelectFile(node.path)}
            >
              <span>{node.name}</span>
              {pendingPaths.has(node.path) && (
                <>
                  {" "}
                  <span className="in-review" title="Change in review">
                    in review
                  </span>
                </>
              )}
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}
