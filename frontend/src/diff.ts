export type DiffLine =
  | { kind: "context"; text: string }
  | { kind: "added"; text: string }
  | { kind: "removed"; text: string };

/** A line-level diff between two file contents, via a longest-common-subsequence walk. */
export function diffLines(base: string | null, proposed: string): DiffLine[] {
  const a = base === null ? [] : base.split("\n");
  const b = proposed.split("\n");
  const n = a.length;
  const m = b.length;

  const lcs: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }

  const result: DiffLine[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      result.push({ kind: "context", text: a[i] });
      i++;
      j++;
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
      result.push({ kind: "removed", text: a[i] });
      i++;
    } else {
      result.push({ kind: "added", text: b[j] });
      j++;
    }
  }
  while (i < n) {
    result.push({ kind: "removed", text: a[i] });
    i++;
  }
  while (j < m) {
    result.push({ kind: "added", text: b[j] });
    j++;
  }
  return result;
}
