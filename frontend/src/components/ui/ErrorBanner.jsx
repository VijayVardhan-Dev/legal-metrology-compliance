export default function ErrorBanner({ error, onDismiss }) {
  if (!error) return null;

  return (
    <div className="alert alert-error" role="alert">
      <span>{error}</span>
      {onDismiss && (
        <button
          className="btn-link"
          onClick={onDismiss}
          aria-label="Dismiss error"
          style={{ marginLeft: 'auto', flexShrink: 0 }}
        >
          ✕
        </button>
      )}
    </div>
  );
}
