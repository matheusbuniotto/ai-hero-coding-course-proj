import { useState } from "react";

import { api, ApiError } from "./api";
import type { Member, WorkspaceRole } from "./api";
import { Loading } from "./Loading";
import { useAsync } from "./useAsync";

const ROLES: WorkspaceRole[] = ["viewer", "editor", "owner"];

export function MembersTab({ workspaceId, role }: { workspaceId: number; role: WorkspaceRole }) {
  const members = useAsync<Member[]>(() => api.members(workspaceId), [workspaceId]);
  const canManage = role === "owner";

  return (
    <section>
      <h1>Members</h1>
      {members.error ? (
        <p className="notice error">{members.error}</p>
      ) : !members.data ? (
        <Loading label="Loading members" lines={2} className="loading-cards" />
      ) : (
        <ul className="member-list">
          {members.data.map((member) => (
            <li key={member.user_id} className="member-entry">
              <span className="member-email">{member.email}</span>
              <span className="role">{member.role}</span>
              {canManage && (
                <button
                  type="button"
                  onClick={() => api.removeMember(workspaceId, member.user_id).then(members.reload)}
                >
                  Remove
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {canManage && <InviteForm workspaceId={workspaceId} onInvited={members.reload} />}
    </section>
  );
}

function InviteForm({ workspaceId, onInvited }: { workspaceId: number; onInvited: () => void }) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<WorkspaceRole>("viewer");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function invite() {
    if (!email.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.inviteMember(workspaceId, email.trim(), role);
      setEmail("");
      onInvited();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      className="invite-form"
      onSubmit={(e) => {
        e.preventDefault();
        void invite();
      }}
    >
      <label>
        Email
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={busy}
        />
      </label>
      <label>
        Role
        <select value={role} onChange={(e) => setRole(e.target.value as WorkspaceRole)} disabled={busy}>
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </label>
      <button type="submit" disabled={busy || !email.trim()}>
        {busy ? "Inviting…" : "Invite"}
      </button>
      {error && <p className="notice error">{error}</p>}
    </form>
  );
}
