/** Format a float (0–1) as a percentage string. Returns "—" for null/undefined. */
export function formatPercent(value) {
  if (value == null) return '—';
  return `${Math.round(value * 100)}%`;
}

/** Replace underscores with spaces and title-case the first letter of each word. */
export function prettify(value) {
  return String(value || '—')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Format an ISO date string to a locale-friendly short date. */
export function formatDate(isoString) {
  if (!isoString) return '—';
  return new Date(isoString).toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/** Format bytes to human-readable file size. */
export function formatFileSize(bytes) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  let size = bytes;
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024;
    i++;
  }
  return `${size.toFixed(i > 0 ? 2 : 0)} ${units[i]}`;
}

/** Truncate a UUID for display (first 8 chars). */
export function shortId(id) {
  return id ? id.slice(0, 8) : '—';
}
