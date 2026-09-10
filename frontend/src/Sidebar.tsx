import type { WorkspaceDetail } from "./api";
import { buildTree } from "./fileTree";
import type { TreeNode } from "./fileTree";

export function Sidebar({ workspace }: { workspace: WorkspaceDetail | null }) {
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
        <Nodes nodes={buildTree(workspace.tree)} label="Files" />
      )}
    </aside>
  );
}

function Nodes({ nodes, label }: { nodes: TreeNode[]; label?: string }) {
  return (
    <ul className="tree" aria-label={label}>
      {nodes.map((node) => (
        <li key={node.path} className={node.kind}>
          {node.name}
          {node.kind === "folder" && <Nodes nodes={node.children} />}
        </li>
      ))}
    </ul>
  );
}
