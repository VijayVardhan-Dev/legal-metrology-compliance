export default function EmptyState({ icon = '○', children = 'Nothing to show yet.' }) {
  return (
    <div className="empty-state" role="status">
      <div className="empty-state-icon" aria-hidden="true">{icon}</div>
      <p>{children}</p>
    </div>
  );
}
