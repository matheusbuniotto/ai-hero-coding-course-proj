import { useState } from "react";
import { useNavigate } from "react-router-dom";

import type { Me } from "./api";

interface TemplateSummary {
  id: string;
  name: string;
  description: string;
}

const TEMPLATES: TemplateSummary[] = [
  { id: "blank", name: "Blank project", description: "Start from nothing." },
  {
    id: "support-agent",
    name: "Support agent",
    description: "Triage and reply workflow with a knowledge base.",
  },
  {
    id: "docs-site",
    name: "Docs site",
    description: "Structured docs with a review workflow baked in.",
  },
  {
    id: "onboarding",
    name: "Onboarding checklist",
    description: "Guided setup flow for new team members.",
  },
  { id: "research", name: "Research notebook", description: "Freeform notes with an agent pair." },
  { id: "changelog", name: "Changelog tracker", description: "Track and publish release notes." },
];

type Filter = "all" | "personal" | "team" | "templates";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "personal", label: "Personal" },
  { key: "team", label: "Team" },
  { key: "templates", label: "Templates" },
];

export function ProjectsHome({ me }: { me: Me }) {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [note, setNote] = useState<string | null>(null);

  const q = query.trim().toLowerCase();
  const showWorkspaces = filter !== "templates";
  const showTemplates = filter === "all" || filter === "templates";

  const workspaces = me.workspaces.filter((w) => {
    if (filter === "personal" && w.kind !== "personal") return false;
    if (filter === "team" && w.kind !== "team") return false;
    return w.name.toLowerCase().includes(q);
  });
  const templates = TEMPLATES.filter((t) => t.name.toLowerCase().includes(q));

  return (
    <div className="projects-home">
      <header className="projects-home-header">
        <h1>Your projects</h1>
        <input
          className="projects-home-search"
          aria-label="Search projects and templates"
          placeholder="Search projects and templates…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </header>

      <div className="projects-home-chips">
        {FILTERS.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            className={`projects-home-chip${filter === key ? " active" : ""}`}
            onClick={() => setFilter(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {note && <div className="projects-home-note">{note}</div>}

      {showWorkspaces && workspaces.length === 0 && !showTemplates && (
        <p className="notice">No projects match "{query}".</p>
      )}

      <div className="projects-home-grid">
        {showWorkspaces &&
          workspaces.map((workspace) => (
            <button
              key={workspace.id}
              type="button"
              className="project-card"
              onClick={() => navigate(`/w/${workspace.id}/library`)}
            >
              <span className="project-card-avatar" aria-hidden="true">
                {workspace.name.charAt(0).toUpperCase()}
              </span>
              <span className="project-card-name">{workspace.name}</span>
              <span className="project-card-meta">
                {workspace.kind} · {workspace.role}
              </span>
            </button>
          ))}
        {showTemplates &&
          templates.map((template) => (
            <button
              key={template.id}
              type="button"
              className="project-card project-card-template"
              onClick={() => setNote(`"${template.name}" — templates are coming soon.`)}
            >
              <span className="project-card-badge">Coming soon</span>
              <span className="project-card-name">{template.name}</span>
              <span className="project-card-desc">{template.description}</span>
            </button>
          ))}
      </div>
    </div>
  );
}
