import { diffLines } from "./diff";

export function DiffView({ base, proposed }: { base: string | null; proposed: string }) {
  const lines = diffLines(base, proposed);
  return (
    <pre className="diff-view">
      {lines.map((line, i) => (
        <div key={i} className={`diff-line diff-${line.kind}`}>
          <span className="diff-marker">
            {line.kind === "added" ? "+" : line.kind === "removed" ? "-" : " "}
          </span>
          {line.text}
        </div>
      ))}
    </pre>
  );
}
