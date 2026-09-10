export type TreeNode =
  | { kind: "folder"; name: string; path: string; children: TreeNode[] }
  | { kind: "file"; name: string; path: string };

type Folder = Extract<TreeNode, { kind: "folder" }>;

/** Turn the API's flat, sorted list of paths into a nested tree. */
export function buildTree(paths: string[]): TreeNode[] {
  const root: Folder = { kind: "folder", name: "", path: "", children: [] };

  for (const path of paths) {
    const segments = path.split("/").filter(Boolean);
    const fileName = segments.pop();
    if (fileName === undefined) continue;

    let folder = root;
    for (const segment of segments) {
      folder = childFolder(folder, segment);
    }
    folder.children.push({ kind: "file", name: fileName, path });
  }

  return root.children;
}

function childFolder(parent: Folder, name: string): Folder {
  const existing = parent.children.find(
    (child): child is Folder => child.kind === "folder" && child.name === name,
  );
  if (existing) return existing;

  const folder: Folder = {
    kind: "folder",
    name,
    path: parent.path ? `${parent.path}/${name}` : name,
    children: [],
  };
  parent.children.push(folder);
  return folder;
}
