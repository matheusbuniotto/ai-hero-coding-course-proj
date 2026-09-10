import { describe, expect, it } from "vitest";

import { diffLines } from "./diff";

describe("diffLines", () => {
  it("treats identical content as all context", () => {
    expect(diffLines("a\nb", "a\nb")).toEqual([
      { kind: "context", text: "a" },
      { kind: "context", text: "b" },
    ]);
  });

  it("marks every line of a new file as added", () => {
    expect(diffLines(null, "a\nb")).toEqual([
      { kind: "added", text: "a" },
      { kind: "added", text: "b" },
    ]);
  });

  it("marks a changed line as a remove followed by an add", () => {
    expect(diffLines("a\nb\nc", "a\nx\nc")).toEqual([
      { kind: "context", text: "a" },
      { kind: "removed", text: "b" },
      { kind: "added", text: "x" },
      { kind: "context", text: "c" },
    ]);
  });

  it("finds an inserted line without disturbing surrounding context", () => {
    expect(diffLines("a\nc", "a\nb\nc")).toEqual([
      { kind: "context", text: "a" },
      { kind: "added", text: "b" },
      { kind: "context", text: "c" },
    ]);
  });

  it("finds a removed line", () => {
    expect(diffLines("a\nb\nc", "a\nc")).toEqual([
      { kind: "context", text: "a" },
      { kind: "removed", text: "b" },
      { kind: "context", text: "c" },
    ]);
  });
});
