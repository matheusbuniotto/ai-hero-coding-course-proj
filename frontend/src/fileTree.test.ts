import { describe, expect, it } from "vitest";

import { buildTree } from "./fileTree";

describe("buildTree", () => {
  it("returns nothing for an empty workspace", () => {
    expect(buildTree([])).toEqual([]);
  });

  it("keeps top-level files flat", () => {
    expect(buildTree(["notes.md"])).toEqual([
      { kind: "file", name: "notes.md", path: "notes.md" },
    ]);
  });

  it("nests files under folders, sharing a folder between siblings", () => {
    const tree = buildTree(["agents/writer/prompt.md", "agents/writer/style.md"]);

    expect(tree).toEqual([
      {
        kind: "folder",
        name: "agents",
        path: "agents",
        children: [
          {
            kind: "folder",
            name: "writer",
            path: "agents/writer",
            children: [
              { kind: "file", name: "prompt.md", path: "agents/writer/prompt.md" },
              { kind: "file", name: "style.md", path: "agents/writer/style.md" },
            ],
          },
        ],
      },
    ]);
  });

  it("keeps folders and files in the order the API sent them", () => {
    const tree = buildTree(["agents/writer/prompt.md", "notes.md"]);

    expect(tree.map((node) => node.name)).toEqual(["agents", "notes.md"]);
  });
});
