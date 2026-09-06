const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

// ---------------------------------------------------------------------------
// Error class
// ---------------------------------------------------------------------------
export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// ---------------------------------------------------------------------------
// Core request helper
// ---------------------------------------------------------------------------
export async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    signal: options.signal || AbortSignal.timeout(180_000),
  });

  // Handle non-JSON responses (e.g. file downloads)
  const contentType = response.headers.get('content-type') || '';
  let body = null;
  if (contentType.includes('application/json')) {
    try { body = await response.json(); } catch { /* noop */ }
  }

  if (!response.ok) {
    const message =
      body?.detail ||
      body?.message ||
      (response.status === 401 ? 'Your session has expired. Please sign in again.' :
       response.status === 409 ? 'This resource already exists.' :
       response.status === 422 ? 'Please check your input and try again.' :
       response.status === 404 ? 'The requested resource was not found.' :
       response.status === 500 ? 'The service encountered an error. Please try again.' :
       `Request failed (${response.status})`);
    throw new ApiError(message, response.status);
  }

  return body;
}

// ---------------------------------------------------------------------------
// Polling helper — awaits a terminal state from a getter function
// ---------------------------------------------------------------------------
export async function poll(getter, isTerminal, { interval = 1500, timeout = 180_000 } = {}) {
  const started = Date.now();
  let value = await getter();
  while (!isTerminal(value)) {
    if (Date.now() - started > timeout) {
      throw new ApiError('Processing timed out. Please open the inspection again.', 408);
    }
    await new Promise(resolve => setTimeout(resolve, interval));
    value = await getter();
  }
  return value;
}

// ---------------------------------------------------------------------------
// Typed API methods
// ---------------------------------------------------------------------------
export const api = {
  // --- Auth ---------------------------------------------------------------
  login: (email, password) =>
    request('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    }),

  register: (email, password) =>
    request('/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    }),

  // --- Dashboard ----------------------------------------------------------
  dashboardSummary: (params) =>
    request(`/api/v1/dashboard/summary${params ? `?${new URLSearchParams(params)}` : ''}`),

  dashboardCompliance: (params) =>
    request(`/api/v1/dashboard/compliance-distribution${params ? `?${new URLSearchParams(params)}` : ''}`),

  dashboardCategories: (params) =>
    request(`/api/v1/dashboard/category-distribution${params ? `?${new URLSearchParams(params)}` : ''}`),

  dashboardRules: (params) =>
    request(`/api/v1/dashboard/rules${params ? `?${new URLSearchParams(params)}` : ''}`),

  dashboardRecent: (limit = 8) =>
    request(`/api/v1/dashboard/recent-inspections?limit=${limit}`),

  /** Fetch all dashboard data in parallel */
  dashboard: () =>
    Promise.all([
      api.dashboardSummary(),
      api.dashboardCompliance(),
      api.dashboardCategories(),
      api.dashboardRules(),
      api.dashboardRecent(),
    ]).then(([summary, compliance, categories, rules, recent]) => ({
      summary, compliance, categories, rules, recent,
    })),

  // --- Inspections --------------------------------------------------------
  listInspections: (params = {}) => {
    const cleaned = Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined)
    );
    return request(`/api/v1/inspections?${new URLSearchParams(cleaned)}`);
  },

  createInspection: (file) => {
    const form = new FormData();
    form.append('image', file);
    form.append('product_name', file.name.replace(/\.[^/.]+$/, '') || 'Uploaded Product');
    form.append('category', 'unknown');
    return request('/api/v1/inspections', { method: 'POST', body: form });
  },

  getInspection: (id) =>
    request(`/api/v1/inspections/${id}`),

  /** Returns raw URL — not an API call */
  imageUrl: (id) =>
    `${API_BASE}/api/v1/inspections/${id}/image`,

  // --- OCR ----------------------------------------------------------------
  triggerOcr: (id) =>
    request(`/api/v1/inspections/${id}/ocr`, { method: 'POST' }),

  getOcr: (id) =>
    request(`/api/v1/inspections/${id}/ocr`),

  // --- Declarations -------------------------------------------------------
  triggerDeclarations: (id) =>
    request(`/api/v1/inspections/${id}/declarations`, { method: 'POST' }),

  getDeclarations: (id) =>
    request(`/api/v1/inspections/${id}/declarations`),

  // --- Category -----------------------------------------------------------
  triggerCategory: (id) =>
    request(`/api/v1/inspections/${id}/category`, { method: 'POST' }),

  getCategory: (id) =>
    request(`/api/v1/inspections/${id}/category`),

  // --- Visual Analysis ----------------------------------------------------
  triggerVisual: (id) =>
    request(`/api/v1/inspections/${id}/visual-analysis`, { method: 'POST' }),

  getVisual: (id) =>
    request(`/api/v1/inspections/${id}/visual-analysis`),

  // --- Compliance ---------------------------------------------------------
  triggerCompliance: (id) =>
    request(`/api/v1/inspections/${id}/compliance`, { method: 'POST' }),

  getCompliance: (id) =>
    request(`/api/v1/inspections/${id}/compliance`),

  // --- Evidence -----------------------------------------------------------
  getEvidence: (id, { rule, declaration, evidence_type } = {}) => {
    const params = new URLSearchParams();
    if (rule) params.set('rule', rule);
    if (declaration) params.set('declaration', declaration);
    if (evidence_type) params.set('evidence_type', evidence_type);
    const qs = params.toString();
    return request(`/api/v1/inspections/${id}/evidence${qs ? `?${qs}` : ''}`);
  },

  // --- Reports ------------------------------------------------------------
  generateReport: (id) =>
    request(`/api/v1/inspections/${id}/report`, { method: 'POST' }),

  getReport: (id) =>
    request(`/api/v1/inspections/${id}/report`),

  reportDownloadUrl: (id) =>
    `${API_BASE}/api/v1/inspections/${id}/report/download`,
};
