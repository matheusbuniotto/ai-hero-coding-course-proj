interface EmptyStateProps {
  icon?: string;
  title: string;
  hint?: string;
}

export function EmptyState({ icon, title, hint }: EmptyStateProps) {
  return (
    <div className="empty-state">
      {icon && (
        <span className="empty-state-icon" aria-hidden="true">
          {icon}
        </span>
      )}
      <p className="empty-state-title">{title}</p>
      {hint && <p className="empty-state-hint">{hint}</p>}
    </div>
  );
}
