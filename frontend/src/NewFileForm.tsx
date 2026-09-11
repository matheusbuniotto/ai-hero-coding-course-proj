import { useState } from "react";

import { api, ApiError } from "./api";

interface NewFileFormProps {
  workspaceId: number;
  onCreated: () => void;
}

/** Lets an editor or owner propose a file that doesn't exist yet, same as any other proposal. */
export function NewFileForm({ workspaceId, onCreated }: NewFileFormProps) {
  const [path, setPath] = useState("");
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function create() {
    const trimmedPath = path.trim();
    if (!trimmedPath) return;
    setBusy(true);
    setError(null);
    try {
      await api.proposeFile(workspaceId, trimmedPath, content);
      setPath("");
      setContent("");
      onCreated();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      className="new-file-form"
      onSubmit={(e) => {
        e.preventDefault();
        void create();
      }}
    >
      <label>
        Path
        <input
          type="text"
          placeholder="notes/todo.md"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          disabled={busy}
        />
      </label>
      <label>
        Content
        <textarea
          rows={6}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          disabled={busy}
        />
      </label>
      <button type="submit" disabled={busy || !path.trim()}>
        {busy ? "Proposing…" : "Propose new file"}
      </button>
      {error && <p className="notice error">{error}</p>}
    </form>
  );
}
