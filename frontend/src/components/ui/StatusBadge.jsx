const STATUS_MAP = {
  COMPLIANT: { className: 'status-compliant', label: 'Compliant' },
  NON_COMPLIANT: { className: 'status-non-compliant', label: 'Non-compliant' },
  REVIEW_REQUIRED: { className: 'status-review-required', label: 'Review required' },
  NOT_APPLICABLE: { className: 'status-not-applicable', label: 'Not applicable' },
  PENDING: { className: 'status-pending', label: 'Pending' },
  PROCESSING: { className: 'status-processing', label: 'Processing' },
  COMPLETED: { className: 'status-completed', label: 'Completed' },
  FAILED: { className: 'status-failed', label: 'Failed' },
  APPLICABLE: { className: 'status-compliant', label: 'Applicable' },
};

export default function StatusBadge({ status }) {
  const normalized = String(status || '').toUpperCase().replace(/\s+/g, '_');
  const info = STATUS_MAP[normalized] || { className: 'status-unknown', label: prettify(status) };

  return (
    <span className={`status-badge ${info.className}`} role="status">
      {info.label}
    </span>
  );
}

function prettify(value) {
  return String(value || '—').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
