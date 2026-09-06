export function SkeletonText({ lines = 3 }) {
  return (
    <div aria-busy="true" aria-label="Loading content">
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="skeleton skeleton-text" />
      ))}
    </div>
  );
}

export function SkeletonCard() {
  return <div className="skeleton skeleton-card" aria-busy="true" aria-label="Loading" />;
}

export function SkeletonTable({ rows = 5 }) {
  return (
    <div aria-busy="true" aria-label="Loading table">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton skeleton-table-row" />
      ))}
    </div>
  );
}
