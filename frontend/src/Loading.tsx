interface LoadingProps {
  label: string;
  lines?: number;
  className?: string;
}

/** A fixed-height skeleton so the swap to real content doesn't jump the layout. */
export function Loading({ label, lines = 3, className }: LoadingProps) {
  return (
    <div className={`loading${className ? ` ${className}` : ""}`} role="status" aria-label={label}>
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="loading-bar" />
      ))}
    </div>
  );
}
