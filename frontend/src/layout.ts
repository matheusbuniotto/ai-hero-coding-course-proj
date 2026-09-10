/**
 * The pane visibility state machine shared by the shell.
 *
 * Three panes — file, output, chat — close and reopen independently, with one
 * hard invariant: at least one must stay visible, so the layout can never go
 * fully blank.
 */

export type Pane = "file" | "output" | "chat";
export type ChatWidth = "normal" | "wide" | "hidden";

export interface PaneState {
  fileOpen: boolean;
  outputOpen: boolean;
  chatWidth: ChatWidth;
}

export function isPaneVisible(state: PaneState, pane: Pane): boolean {
  if (pane === "file") return state.fileOpen;
  if (pane === "output") return state.outputOpen;
  return state.chatWidth !== "hidden";
}

export function visibleCount(state: PaneState): number {
  return (["file", "output", "chat"] as const).filter((pane) => isPaneVisible(state, pane)).length;
}

/** False when `pane` is the last visible one — closing it would blank the layout. */
export function canClose(state: PaneState, pane: Pane): boolean {
  return !isPaneVisible(state, pane) || visibleCount(state) > 1;
}

export function closedPanes(state: PaneState): Pane[] {
  return (["file", "output", "chat"] as const).filter((pane) => !isPaneVisible(state, pane));
}

export const PANE_LABELS: Record<Pane, string> = {
  file: "File",
  output: "Sandbox output",
  chat: "Chat",
};
