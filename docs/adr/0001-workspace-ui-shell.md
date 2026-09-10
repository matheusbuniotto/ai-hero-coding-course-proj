# ADR-0001: Workspace UI shell — wiki nav + review inbox + first-class chat

- **Status**: Accepted
- **Date**: 2026-09-09
- **Context source**: [issue #1](https://github.com/matheusbuniotto/ai-hero-couse-proj/issues/1) (v1 platform spec)

## Context

Issue #1 defines the platform but says nothing about the shape of its main screen. The
workspace surface has to carry four jobs at once, for users with different roles:

- **Browse** the workspace tree — instruction files and business content (stories 3, 4).
- **Run** a live, code-executing session against an agent (stories 5–8).
- **Review** one consolidated session diff and approve or reject it, all-or-nothing (stories 9–11, 15, 24).
- **Govern** — roles, membership, and the history of approved changes (stories 12–14, 23).

These pull in opposite directions. An agent-session UI wants a dense, uninterrupted
working surface. A governance UI wants stable navigation and a place where a Viewer or a
non-running Owner can land without ever opening a session.

Three variants were prototyped side by side on `/prototype/workspace-ui?variant=A|B|C`
against mock data:

- **A — Cockpit**: dark three-pane IDE. Tree | session | permanent diff panel.
- **B — Conversation-first**: full-bleed chat, no persistent chrome, workspace behind ⌘K,
  the diff arriving inline as a "Save this session?" card.
- **C — Wiki + review inbox**: docs-site shell (Library / Review / History / Members tabs,
  file sidebar), with chat as a full-height right column.

## Decision

Adopt **variant C**: a wiki-style application shell with a **first-class chat column**,
and B's **inline approval card** inside that column.

Concretely:

- **Top-level tabs** are the primary navigation: Library, Review, History, Members. Review
  carries a pending-count badge. Approval is a destination, not a panel — a Viewer or
  Owner who never starts a session still has a complete UI.
- **Left sidebar** lists agents (subfolders) then the workspace tree, mirroring the fact
  that a workspace holds several specialized agents.
- **Chat is a column, not a dock** — a full-height right rail carrying the whole
  transcript, sandbox executions, and a composer. It is the primary working surface, not
  an accessory. Width cycles normal → wide → hidden.
- **Approval happens twice, deliberately**: a lightweight inline "Save this session?" card
  at the end of the transcript (the solo self-confirm from story 11), and a full-diff
  review in the Review tab (the team path, story 10). Both are all-or-nothing over the
  whole session diff; neither ever auto-applies.
- **Panes are independently closable** (file tab, sandbox output panel, chat), VS Code
  style, with a bottom status bar as the way back. Closing the file and the output panel
  leaves nav + chat, which is the "just work with the agent" mode. The UI never allows a
  fully empty screen.
- **Sandbox output** gets its own panel — the full command log with exit codes, durations,
  stdout, and stderr — distinct from the exec turns summarised inline in the chat.

## Alternatives rejected

- **A (Cockpit)**: an always-visible diff panel makes every session feel like a pull
  request, and the dark IDE framing assumes a technical user. Issue #1's users are
  business teams; the spec's whole premise is that no one should need git to use this.
  Its dense session pane is the part worth keeping, and C keeps it as the chat column.
- **B (Conversation-first)**: the best *session* experience of the three, but it has no
  home for a Viewer, no reachable history, and hides the workspace tree behind a command
  palette — directly against story 3 ("see the folder tree that defines our agent"). Its
  inline review card was adopted into C rather than the layout.

## Consequences

- The shell is navigation-heavy, so the chat column must be given real width by default
  (~480px, widenable) or C degrades into A's cramped middle pane. This is the main risk to
  watch when it is built for real.
- Two approval entry points (inline card, Review tab) must render the same all-or-nothing
  proposal and cannot diverge. One proposal model, two views.
- Roles map to visible chrome: Viewers see Library/Review/History with no composer and no
  approve buttons; Editors get the composer; Owners get the approve buttons.
- The chat column and the review inbox both need the session diff, so the consolidated
  diff needs to be fetchable independently of the session transcript. The existing
  `GET /workspace/agent/sessions/{id}/proposal` already provides this.
- No decision is recorded here about whether the document pane should auto-follow the file
  the agent is editing. Left open deliberately.

## Prototype

The three variants are throwaway code and do not belong on `main`. They are captured on a
separate branch as the primary source behind this decision; only the validated shape lands
in production code.
