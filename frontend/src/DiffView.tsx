import { useState, type ReactNode } from "react";

import { diffLines } from "./diff";

interface DiffViewProps {
  path: string;
  base: string | null;
  proposed: string;
  /** Context-specific controls (status badge, approve/reject buttons) rendered next to the path. */
  headerActions?: ReactNode;
}

export function DiffView({ path, base, proposed, headerActions }: DiffViewProps) {
  const [collapsed, setCollapsed] = useState(false);
  const lines = diffLines(base, proposed);

  let oldNum = 0;
  let newNum = 0;
  const numbered = lines.map((line) => {
    if (line.kind === "context") {
      oldNum++;
      newNum++;
      return { ...line, oldNum, newNum };
    }
    if (line.kind === "removed") {
      oldNum++;
      return { ...line, oldNum, newNum: null };
    }
    newNum++;
    return { ...line, oldNum: null, newNum };
  });

  return (
    <div className="diff-view">
      <div className="diff-view-header">
        <button
          type="button"
          className="diff-view-toggle"
          aria-expanded={!collapsed}
          onClick={() => setCollapsed((c) => !c)}
        >
          <span className="diff-view-chevron" aria-hidden="true">
            {collapsed ? "▸" : "▾"}
          </span>
          <span className="diff-view-path">{path}</span>
        </button>
        {headerActions}
      </div>
      {!collapsed && (
        <pre className="diff-view-body">
          <ul className="diff-lines">
            {numbered.map((line, i) => (
              <li key={i} className={`diff-line diff-${line.kind}`}>
                <span className="diff-line-num diff-line-num-old">{line.oldNum ?? ""}</span>
                <span className="diff-line-num diff-line-num-new">{line.newNum ?? ""}</span>
                <span className="diff-marker">
                  {line.kind === "added" ? "+" : line.kind === "removed" ? "-" : " "}
                </span>
                <span className="diff-line-text">{line.text}</span>
              </li>
            ))}
          </ul>
        </pre>
      )}
    </div>
  );
}
