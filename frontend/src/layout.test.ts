import { describe, expect, it } from "vitest";

import { canClose, closedPanes, visibleCount } from "./layout";
import type { PaneState } from "./layout";

const ALL_OPEN: PaneState = { fileOpen: true, outputOpen: true, chatWidth: "normal" };

describe("visibleCount", () => {
  it("counts every visible pane", () => {
    expect(visibleCount(ALL_OPEN)).toBe(3);
  });

  it("treats a hidden chat as not visible regardless of width history", () => {
    expect(visibleCount({ ...ALL_OPEN, chatWidth: "hidden" })).toBe(2);
  });

  it("counts a wide chat as visible, same as normal", () => {
    expect(visibleCount({ ...ALL_OPEN, chatWidth: "wide" })).toBe(3);
  });
});

describe("canClose", () => {
  it("allows closing a pane when others remain visible", () => {
    expect(canClose(ALL_OPEN, "output")).toBe(true);
  });

  it("refuses to close the only visible pane", () => {
    const onlyChat: PaneState = { fileOpen: false, outputOpen: false, chatWidth: "normal" };
    expect(canClose(onlyChat, "chat")).toBe(false);
  });

  it("allows closing an already-closed pane (a no-op)", () => {
    const onlyChat: PaneState = { fileOpen: false, outputOpen: false, chatWidth: "normal" };
    expect(canClose(onlyChat, "file")).toBe(true);
  });

  it("refuses to close the last of two once the other is already gone", () => {
    const fileAndChat: PaneState = { fileOpen: true, outputOpen: false, chatWidth: "normal" };
    expect(canClose(fileAndChat, "file")).toBe(true);
    expect(canClose(fileAndChat, "chat")).toBe(true);

    const chatOnly: PaneState = { fileOpen: false, outputOpen: false, chatWidth: "normal" };
    expect(canClose(chatOnly, "chat")).toBe(false);
  });
});

describe("closedPanes", () => {
  it("lists nothing when every pane is visible", () => {
    expect(closedPanes(ALL_OPEN)).toEqual([]);
  });

  it("lists each pane that is currently closed, in a stable order", () => {
    const state: PaneState = { fileOpen: false, outputOpen: true, chatWidth: "hidden" };
    expect(closedPanes(state)).toEqual(["file", "chat"]);
  });
});
