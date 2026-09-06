import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './hooks/useAuth';
import { ProtectedRoute } from './router/ProtectedRoute';
import AppShell from './components/layout/AppShell';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import NewInspectionPage from './pages/NewInspectionPage';
import InspectionPage from './pages/InspectionPage';
import HistoryPage from './pages/HistoryPage';
import ReportsPage from './pages/ReportsPage';
import SettingsPage from './pages/SettingsPage';

export default function App() {
import { useMemo, useRef, useState } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const STEPS = [["upload", "Upload"], ["ocr", "OCR"], ["declarations", "Declarations"], ["category", "Category"], ["visual", "Visual Analysis"], ["nutrition", "Nutrition"], ["compliance", "Compliance"]];

function statusClass(status) {
  return {
    COMPLIANT: "status status-green",
    NON_COMPLIANT: "status status-red",
    REVIEW_REQUIRED: "status status-yellow",
    NOT_APPLICABLE: "status status-muted",
    FOUND: "status status-green",
    INCOMPLETE: "status status-yellow",
    GOOD: "status status-green",
    POOR: "status status-red",
  }[status] || "status status-muted";
}

function prettyLabel(value) {
  return String(value || "").replaceAll("_", " ");
}

function LoginPage({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    const email = username.trim().toLowerCase();
    if (mode === "register" && password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const result = await request(`/api/v1/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      onLogin(rememberMe, result.user);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected — wrapped in AppShell */}
          <Route
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="inspections/new" element={<NewInspectionPage />} />
            <Route path="inspections/:id" element={<InspectionPage />} />
            <Route path="inspections" element={<HistoryPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<LoginPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
    <main className="login-shell">
      <section className="login-visual">
        <div className="login-visual-top"><div className="brand-mark">LM</div><span>COMPLIANCE CONTROL</span></div>
        <div className="login-visual-copy"><p className="eyebrow">LEGAL METROLOGY / INDIA</p><h1>Make every label<br /><em>count.</em></h1><p>Inspect packaged commodities with a clear chain from evidence to decision.</p></div>
        <div className="login-signal"><span className="signal-dot" /> OCR pipeline ready <strong>01</strong></div>
      </section>
      <section className="login-panel">
        <div className="login-form-wrap">
          <p className="eyebrow">INSPECTOR ACCESS</p>
          <h2>{mode === "login" ? "Welcome back" : "Create account"}</h2>
          <p className="login-intro">{mode === "login" ? "Sign in to open your inspection workbench." : "Create an account to start inspecting package labels."}</p>
          <form className="login-form" onSubmit={submit}>
            <label htmlFor="username">Email address<input id="username" type="email" autoComplete="email" value={username} onChange={(event) => { setUsername(event.target.value); setError(""); }} placeholder="you@example.com" required /></label>
            <label htmlFor="password">Password<div className="password-input"><input id="password" type={showPassword ? "text" : "password"} autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(event) => { setPassword(event.target.value); setError(""); }} placeholder="At least 8 characters" minLength="8" required /><button type="button" className="visibility-button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? "Hide" : "Show"}</button></div></label>
            {mode === "register" && <label htmlFor="confirm-password">Confirm password<input id="confirm-password" type={showPassword ? "text" : "password"} autoComplete="new-password" value={confirmPassword} onChange={(event) => { setConfirmPassword(event.target.value); setError(""); }} placeholder="Re-enter your password" minLength="8" required /></label>}
            <div className="login-options"><label className="checkbox-label"><input type="checkbox" checked={rememberMe} onChange={(event) => setRememberMe(event.target.checked)} /> Remember me</label>{mode === "login" && <button type="button" className="forgot-button" onClick={() => setError("Password recovery is not configured yet.")}>Forgot password?</button>}</div>
            {error && <div className="login-error" role="alert">{error}</div>}
            <button className="login-submit" type="submit" disabled={submitting}>{submitting ? "Please wait..." : mode === "login" ? "Sign in" : "Create account"} <span>→</span></button>
          </form>
          <p className="login-switch">{mode === "login" ? "New to the workbench?" : "Already have an account?"} <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}> {mode === "login" ? "Create an account" : "Sign in"}</button></p>
          <p className="login-footer">Protected inspection workspace <span>•</span> v1.0</p>
        </div>
      </section>
    </main>
  );
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    signal: options.signal || AbortSignal.timeout(180000),
  });
  let body = null;
  try { body = await response.json(); } catch { body = null; }
  if (!response.ok) throw new Error(body?.detail || `Request failed (${response.status})`);
  return body;
}

function App() {
  const [authenticated, setAuthenticated] = useState(() => Boolean(localStorage.getItem("lm_user_email")));
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [inspectionId, setInspectionId] = useState("");
  const [ocr, setOcr] = useState(null);
  const [declarations, setDeclarations] = useState([]);
  const [category, setCategory] = useState(null);
  const [visualAnalysis, setVisualAnalysis] = useState(null);
  const [nutritionAnalysis, setNutritionAnalysis] = useState(null);
  const [compliance, setCompliance] = useState(null);
  const [report, setReport] = useState(null);
  const [reportRunning, setReportRunning] = useState(false);
  const [selectedEvidence, setSelectedEvidence] = useState([]);
  const [evidenceRule, setEvidenceRule] = useState("");
  const [activeStep, setActiveStep] = useState("upload");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [view, setView] = useState("workbench");
  const [history, setHistory] = useState({ items: [], page: 1, page_size: 10, total: 0, total_pages: 0 });
  const [dashboard, setDashboard] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyQuery, setHistoryQuery] = useState({ search: "", compliance_status: "", category: "" });

  function login(rememberMe, user) {
    if (rememberMe) {
      localStorage.setItem("lm_authenticated", "true");
      localStorage.setItem("lm_user_email", user.email);
    }
    setAuthenticated(true);
  }

  function logout() {
    localStorage.removeItem("lm_authenticated");
    localStorage.removeItem("lm_user_email");
    setAuthenticated(false);
    reset();
  }

  const completedSteps = useMemo(() => new Set([
    ...(inspectionId ? ["upload"] : []),
    ...(ocr ? ["ocr"] : []),
    ...(declarations.length ? ["declarations"] : []),
    ...(category ? ["category"] : []),
    ...(visualAnalysis ? ["visual"] : []),
    ...(nutritionAnalysis ? ["nutrition"] : []),
    ...(compliance ? ["compliance"] : []),
  ]), [inspectionId, ocr, declarations, category, visualAnalysis, nutritionAnalysis, compliance]);

  function chooseFile(nextFile) {
    if (!nextFile || !nextFile.type.startsWith("image/")) {
      setError("Please choose a supported image file.");
      return;
    }
    setFile(nextFile);
    setPreview(URL.createObjectURL(nextFile));
    setError("");
    setInspectionId(""); setOcr(null); setDeclarations([]); setCategory(null); setVisualAnalysis(null); setNutritionAnalysis(null); setCompliance(null); setReport(null); setSelectedEvidence([]); setEvidenceRule(""); setActiveStep("upload");
  }

  function reset() {
    setFile(null); setPreview(""); setInspectionId(""); setOcr(null); setDeclarations([]); setCategory(null); setVisualAnalysis(null); setNutritionAnalysis(null); setCompliance(null); setReport(null); setSelectedEvidence([]); setEvidenceRule("");
    setActiveStep("upload"); setError("");
    if (inputRef.current) inputRef.current.value = "";
  }

  async function loadHistory(page = 1) {
    setHistoryLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ page: String(page), page_size: "10", sort_by: "created_at", sort_order: "desc" });
      Object.entries(historyQuery).forEach(([key, value]) => { if (value) params.set(key, value); });
      const [historyResult, summaryResult] = await Promise.all([
        request(`/api/v1/inspections?${params.toString()}`),
        request("/api/v1/dashboard/summary"),
      ]);
      setHistory(historyResult);
      setDashboard(summaryResult);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setHistoryLoading(false);
    }
  }

  function showHistory() {
    setView("history");
    loadHistory(1);
  }

  async function viewEvidence(ruleId) {
    if (!inspectionId) return;
    setError("");
    try {
      const items = await request(`/api/v1/inspections/${inspectionId}/evidence?rule=${encodeURIComponent(ruleId)}`);
      setEvidenceRule(ruleId);
      setSelectedEvidence(items || []);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function generateReport() {
    if (!inspectionId || !compliance) return;
    setReportRunning(true);
    setError("");
    try {
      const generated = await request(`/api/v1/inspections/${inspectionId}/report`, { method: "POST" });
      setReport(generated);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setReportRunning(false);
    }
  }

  function downloadReport() {
    if (!inspectionId) return;
    window.open(`${API_BASE_URL}/api/v1/inspections/${inspectionId}/report/download`, "_blank", "noopener,noreferrer");
  }

  async function runInspection() {
    if (!file) { setError("Upload a package image before starting the inspection."); return; }
    setRunning(true); setError("");
    try {
      const form = new FormData();
      form.append("image", file);
      form.append("product_name", file.name.replace(/\.[^/.]+$/, "") || "Uploaded Product");
      form.append("category", "unknown");
      const created = await request("/api/v1/inspections", { method: "POST", body: form });
      setInspectionId(created.inspection_id); setActiveStep("ocr");
      const ocrResult = await request(`/api/v1/inspections/${created.inspection_id}/ocr`, { method: "POST" });
      setOcr(ocrResult);
      if (ocrResult.status !== "COMPLETED") {
        throw new Error(ocrResult.error_message || "OCR processing failed. Check the backend logs for details.");
      }
      setActiveStep("declarations");
      const declarationResult = await request(`/api/v1/inspections/${created.inspection_id}/declarations`, { method: "POST" });
      setDeclarations(declarationResult.declarations || []); setActiveStep("category");
      const [categoryResult, visualResult] = await Promise.all([
        request(`/api/v1/inspections/${created.inspection_id}/category`, { method: "POST" }),
        request(`/api/v1/inspections/${created.inspection_id}/visual-analysis`, { method: "POST" }),
      ]);
      setCategory(categoryResult); setVisualAnalysis(visualResult); setActiveStep("nutrition");
      try {
        const nutritionResult = await request(`/api/v1/inspections/${created.inspection_id}/nutrition-analysis`, { method: "POST" });
        setNutritionAnalysis(nutritionResult);
      } catch (nutritionError) {
        setNutritionAnalysis({ status: "FAILED", error_message: nutritionError.message, warnings: ["Nutrition analysis was unavailable. Legal Metrology compliance was still completed."] });
      }
      setActiveStep("compliance");
      const complianceResult = await request(`/api/v1/inspections/${created.inspection_id}/compliance`, { method: "POST" });
      setCompliance(complianceResult);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setRunning(false);
    }
  }

  if (!authenticated) return <LoginPage onLogin={login} />;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark">LM</div>
        <div><div className="eyebrow">INSPECTION WORKBENCH</div><h1>Legal Metrology Compliance</h1></div>
        <div className="topbar-actions">
          <button className={`nav-button ${view === "workbench" ? "nav-button-active" : ""}`} onClick={() => setView("workbench")}>Workbench</button>
          <button className={`nav-button ${view === "history" ? "nav-button-active" : ""}`} onClick={showHistory}>Inspection history</button>
          <div className="api-indicator"><span /> API {API_BASE_URL}</div>
        </div>
        <button className="logout-button" onClick={logout}>Sign out</button>
      </header>
      <main className="page">
        <section className="hero">
          <div><p className="eyebrow">PHASE 1–6 TESTING FRONTEND</p><h2>Inspect a package label end to end.</h2><p className="hero-copy">Upload one package image to run OCR, declaration extraction, and deterministic compliance evaluation in sequence.</p></div>
          {inspectionId && <div className="inspection-chip">Inspection <strong>{inspectionId.slice(0, 8)}…</strong></div>}
        </section>
        {view === "history" ? <section className="history-view">
          <div className="history-heading"><div><p className="eyebrow">PHASE 10</p><h2>Inspection history</h2><p className="hero-copy">Review persisted inspections, compliance outcomes, confidence, and processing status.</p></div><button className="secondary-button" onClick={() => setView("workbench")}>New inspection</button></div>
          {dashboard && <div className="history-summary metric-grid">
            <div><span>Total inspections</span><strong>{dashboard.total_inspections}</strong></div>
            <div><span>Compliant</span><strong>{dashboard.compliant_inspections}</strong></div>
            <div><span>Non-compliant</span><strong>{dashboard.non_compliant_inspections}</strong></div>
            <div><span>Review required</span><strong>{dashboard.review_required_inspections}</strong></div>
            <div><span>Without compliance</span><strong>{dashboard.inspections_without_completed_compliance}</strong></div>
            <div><span>Reports generated</span><strong>{dashboard.reports_generated}</strong></div>
          </div>}
          <section className="card history-card">
            <div className="history-filters">
              <input value={historyQuery.search} onChange={(event) => setHistoryQuery({ ...historyQuery, search: event.target.value })} placeholder="Search product, brand, ID, report…" />
              <select value={historyQuery.compliance_status} onChange={(event) => setHistoryQuery({ ...historyQuery, compliance_status: event.target.value })}><option value="">All compliance statuses</option><option value="COMPLIANT">Compliant</option><option value="NON_COMPLIANT">Non-compliant</option><option value="REVIEW_REQUIRED">Review required</option></select>
              <input value={historyQuery.category} onChange={(event) => setHistoryQuery({ ...historyQuery, category: event.target.value })} placeholder="Category" />
              <button className="primary-button history-filter-button" onClick={() => loadHistory(1)} disabled={historyLoading}>{historyLoading ? "Loading…" : "Apply filters"}</button>
            </div>
            {historyLoading ? <div className="empty-state">Loading inspection history…</div> : history.items.length === 0 ? <div className="empty-state">No inspections match the selected filters.</div> : <div className="table-scroll"><table><thead><tr><th>Inspection</th><th>Product</th><th>Compliance</th><th>Confidence</th><th>Processing</th><th>Rules</th><th>Report</th></tr></thead><tbody>{history.items.map((item) => <tr key={item.inspection_id}><td><strong>{item.inspection_id.slice(0, 8)}…</strong><small className="unit">{new Date(item.created_at).toLocaleString()}</small></td><td><strong>{item.product_name}</strong><small className="unit">{prettyLabel(item.category)}{item.subcategory ? ` · ${item.subcategory}` : ""}</small></td><td>{item.overall_compliance_status ? <span className={statusClass(item.overall_compliance_status)}>{prettyLabel(item.overall_compliance_status)}</span> : <span className="status status-muted">Not evaluated</span>}</td><td>{item.overall_confidence != null ? `${(item.overall_confidence * 100).toFixed(1)}%` : "—"}</td><td><small>OCR: {item.ocr_status || "—"}</small><small className="unit">Visual: {item.visual_analysis_status || "—"}</small></td><td><small>✓ {item.compliant_rule_count} · ✕ {item.non_compliant_rule_count}</small><small className="unit">Review: {item.review_required_rule_count}</small></td><td>{item.report_number || "—"}</td></tr>)}</tbody></table></div>}
            {history.total_pages > 1 && <div className="pagination"><button className="secondary-button" disabled={history.page <= 1 || historyLoading} onClick={() => loadHistory(history.page - 1)}>Previous</button><span>Page {history.page} of {history.total_pages} · {history.total} inspections</span><button className="secondary-button" disabled={history.page >= history.total_pages || historyLoading} onClick={() => loadHistory(history.page + 1)}>Next</button></div>}
          </section>
        </section> : <><section className="stepper card">
          {STEPS.map(([key, label], index) => <div className={`step ${activeStep === key ? "step-active" : ""} ${completedSteps.has(key) ? "step-complete" : ""}`} key={key}><div className="step-number">{completedSteps.has(key) ? "✓" : index + 1}</div><span>{label}</span>{index < STEPS.length - 1 && <div className="step-line" />}</div>)}
        </section>
        {error && <div className="error-banner"><strong>Inspection stopped.</strong> {error}</div>}
        <section className="workspace-grid">
          <div className="left-column">
            <section className="card upload-card">
              <div className="section-heading"><div><p className="eyebrow">INPUT</p><h3>Package image</h3></div>{file && <button className="text-button" onClick={reset}>Reset</button>}</div>
              {preview ? <div className="preview-wrap"><img src={preview} alt="Selected package" /><div className="file-pill">{file.name}</div></div> : <button className="dropzone" onClick={() => inputRef.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); chooseFile(event.dataTransfer.files[0]); }}><span className="upload-icon">↑</span><strong>Drop package image here</strong><span>or click to browse · JPG, PNG, WEBP</span></button>}
              <input ref={inputRef} type="file" accept="image/*" hidden onChange={(event) => chooseFile(event.target.files[0])} />
              <button className="primary-button" disabled={!file || running} onClick={runInspection}>{running ? "Running inspection…" : inspectionId ? "Run Again" : "Start Inspection"}</button>
            </section>
            <section className="card">
              <div className="section-heading"><div><p className="eyebrow">OCR PROCESSING</p><h3>Recognition status</h3></div>{ocr && <span className={statusClass(ocr.status)}>{ocr.status}</span>}</div>
              <div className="metric-grid"><div><span>Status</span><strong>{ocr?.status || "Waiting"}</strong></div><div><span>Average confidence</span><strong>{ocr?.average_confidence != null ? `${(ocr.average_confidence * 100).toFixed(1)}%` : "—"}</strong></div><div><span>Processing time</span><strong>{ocr?.processing_time_ms != null ? `${ocr.processing_time_ms} ms` : "—"}</strong></div></div>
            </section>
            <section className="card">
              <div className="section-heading"><div><p className="eyebrow">CLASSIFICATION</p><h3>Product category</h3></div>{category && <span className={statusClass(category.status)}>{category.status}</span>}</div>
              {category ? <div className="metric-grid"><div><span>Category</span><strong>{category.category}</strong></div><div><span>Subcategory</span><strong>{category.subcategory || "—"}</strong></div><div><span>Confidence</span><strong>{category.confidence != null ? `${(category.confidence * 100).toFixed(1)}%` : "—"}</strong></div></div> : <div className="empty-state">Category classification will run after declarations.</div>}
            </section>
          </div>
          <div className="right-column">
            <section className="card">
              <div className="section-heading"><div><p className="eyebrow">PHASE 5</p><h3>Extracted declarations</h3></div><span className="count-badge">{declarations.length}</span></div>
              {declarations.length ? <div className="table-scroll"><table><thead><tr><th>Type</th><th>Value</th><th>Confidence</th><th>Status</th><th>Source text</th></tr></thead><tbody>{declarations.map((item) => <tr key={item.id || `${item.declaration_type}-${item.source_text}`}><td className="type-cell">{prettyLabel(item.declaration_type)}</td><td><strong>{item.value || "Not confidently extracted"}</strong>{item.unit && <small className="unit">{item.unit}</small>}</td><td>{item.confidence != null ? `${(item.confidence * 100).toFixed(1)}%` : "—"}</td><td><span className={statusClass(item.status)}>{item.status}</span></td><td className="source-cell">{item.source_text || "—"}</td></tr>)}</tbody></table></div> : <div className="empty-state">Declarations will appear here after OCR completes.</div>}
            </section>
            <section className="card nutrition-card">
              <div className="section-heading"><div><p className="eyebrow">NUTRITION & INGREDIENT ANALYZER</p><h3>Nutrition analysis</h3></div>{nutritionAnalysis?.status && <span className={statusClass(nutritionAnalysis.status === "COMPLETED" ? "FOUND" : "REVIEW_REQUIRED")}>{nutritionAnalysis.status}</span>}</div>
              {!nutritionAnalysis ? <div className="empty-state">Nutrition, ingredients, and allergens will be analyzed from the completed OCR text.</div> : nutritionAnalysis.status === "FAILED" ? <div className="error-banner">{nutritionAnalysis.error_message || "Nutrition analysis could not be completed."}</div> : <div>
                <div className="metric-grid"><div><span>Nutrition confidence</span><strong>{nutritionAnalysis.nutrition_confidence != null ? `${(nutritionAnalysis.nutrition_confidence * 100).toFixed(1)}%` : "—"}</strong></div><div><span>Ingredient confidence</span><strong>{nutritionAnalysis.ingredient_confidence != null ? `${(nutritionAnalysis.ingredient_confidence * 100).toFixed(1)}%` : "—"}</strong></div><div><span>Allergens detected</span><strong>{nutritionAnalysis.allergens?.length || 0}</strong></div></div>
                {nutritionAnalysis.warnings?.length > 0 && <ul className="warning-list">{nutritionAnalysis.warnings.map((warning, index) => <li key={`${warning}-${index}`}>{warning}</li>)}</ul>}
                <h4>Nutrition information</h4>
                <div className="table-scroll"><table><thead><tr><th>Nutrient</th><th>Amount</th><th>Basis</th><th>Confidence</th></tr></thead><tbody>{Object.entries(nutritionAnalysis.nutrition || {}).map(([name, item]) => <tr key={name}><td className="type-cell">{name}</td><td><strong>{item.value || "Not detected"}</strong>{item.unit && ` ${item.unit}`}</td><td>{item.basis || "Not detected"}</td><td>{item.confidence ? `${(item.confidence * 100).toFixed(1)}%` : "—"}</td></tr>)}</tbody></table></div>
                <h4>Ingredient analysis</h4>
                <div className="table-scroll"><table><thead><tr><th>Ingredient</th><th>Category</th><th>Purpose</th><th>Assessment</th></tr></thead><tbody>{nutritionAnalysis.ingredients?.length ? nutritionAnalysis.ingredients.map((item, index) => <tr key={`${item.name}-${index}`}><td className="type-cell">{item.name}</td><td>{item.category}</td><td>{item.purpose}</td><td><span className={`status status-${item.assessment === "moderation" ? "yellow" : item.assessment === "insufficient_information" ? "muted" : item.assessment === "additive" ? "blue" : "green"}`}>{item.assessment}</span><small className="unit">{item.reason}</small></td></tr>) : <tr><td colSpan="4">Not detected</td></tr>}</tbody></table></div>
                <h4>Allergens</h4>
                {nutritionAnalysis.allergens?.length ? <div className="warning-list"><strong>Allergens detected:</strong> {nutritionAnalysis.allergens.map((item) => item.name).join(", ")}</div> : <div className="empty-state">No allergens were explicitly detected in the extracted label text.</div>}
                <h4>Consumer insights</h4>
                <ul className="warning-list">{(nutritionAnalysis.insights || ["Unable to determine from the available label information."]).map((insight, index) => <li key={`${insight}-${index}`}>{insight}</li>)}</ul>
                <h4>Raw detected ingredient list</h4><p className="analysis-note">{nutritionAnalysis.ingredient_text || "Not detected"}</p>
              </div>}
            </section>
            <section className="card">
              <div className="section-heading"><div><p className="eyebrow">PHASE 7</p><h3>Visual analysis</h3></div>{visualAnalysis?.quality_status && <span className={statusClass(visualAnalysis.quality_status)}>{visualAnalysis.quality_status}</span>}</div>
              {!visualAnalysis ? <div className="empty-state">Image quality and declaration visibility will be assessed after classification.</div> : <div>
                <div className="metric-grid">
                  <div><span>Quality score</span><strong>{visualAnalysis.quality_score != null ? `${(Number(visualAnalysis.quality_score) * 100).toFixed(1)}%` : "—"}</strong></div>
                  <div><span>Resolution</span><strong>{visualAnalysis.image_width && visualAnalysis.image_height ? `${visualAnalysis.image_width} × ${visualAnalysis.image_height}` : "—"}</strong></div>
                  <div><span>Blur / sharpness</span><strong>{visualAnalysis.metrics?.blur_score != null ? Number(visualAnalysis.metrics.blur_score).toFixed(1) : "—"}</strong></div>
                  <div><span>Brightness / contrast</span><strong>{visualAnalysis.metrics?.brightness_score != null ? `${Number(visualAnalysis.metrics.brightness_score).toFixed(2)} / ${visualAnalysis.metrics?.contrast_score != null ? Number(visualAnalysis.metrics.contrast_score).toFixed(2) : "—"}` : "—"}</strong></div>
                </div>
                <p className="analysis-note">Text size: <strong>APPROXIMATE / SCREEN-BASED ANALYSIS</strong>. Physical millimetre compliance is not inferred without calibration.</p>
                {visualAnalysis.warnings?.length > 0 && <ul className="warning-list">{visualAnalysis.warnings.map((warning, index) => <li key={`${warning}-${index}`}>{warning}</li>)}</ul>}
                {visualAnalysis.declarations?.length > 0 && <div className="table-scroll"><table><thead><tr><th>Declaration</th><th>Visibility</th><th>Text size</th><th>Evidence</th></tr></thead><tbody>{visualAnalysis.declarations.map((item) => <tr key={item.declaration_id || item.id}><td className="type-cell">{prettyLabel(item.declaration_type || item.field_name)}</td><td><span className={statusClass(item.status || item.visibility_flag)}>{prettyLabel(item.status || item.visibility_flag)}</span></td><td>{item.relative_text_height != null ? `${Number(item.relative_text_height).toFixed(2)}% image height` : "—"}</td><td>{item.ocr_region_ids?.length ? item.ocr_region_ids.join(", ") : item.ocr_text_region_id || "—"}</td></tr>)}</tbody></table></div>}
              </div>}
            </section>
            <section className="card">
              <div className="section-heading"><div><p className="eyebrow">PHASE 8</p><h3>Compliance summary</h3></div>{compliance?.overall_status && <span className={statusClass(compliance.overall_status)}>{compliance.overall_status}</span>}</div>
              {!compliance ? <div className="empty-state">Rule evaluation will appear here after declarations are stored.</div> : <div>
                <div className="metric-grid compliance-summary">
                  <div><span>Rules</span><strong>{compliance.total_rules}</strong></div>
                  <div><span>Compliant</span><strong>{compliance.compliant_rules}</strong></div>
                  <div><span>Non-compliant</span><strong>{compliance.non_compliant_rules}</strong></div>
                  <div><span>Review required</span><strong>{compliance.review_required_rules}</strong></div>
                  <div><span>Confidence</span><strong>{compliance.overall_confidence != null ? `${(compliance.overall_confidence * 100).toFixed(1)}%` : "—"}</strong></div>
                </div>
                <div className="rule-list">{(compliance.results || []).map((result) => <article className="rule-card" key={result.rule_id}><div className="rule-top"><div><strong>{result.rule_id}</strong><span className="legal-reference">{result.legal_reference}</span></div><span className={statusClass(result.status)}>{result.status}</span></div><p>{result.reason}</p><div className="rule-meta"><span>Severity: <strong>{result.severity}</strong></span><span>Applicability: <strong>{result.applicability_status || "APPLICABLE"}</strong></span><span>Confidence: <strong>{result.confidence != null ? `${(result.confidence * 100).toFixed(1)}%` : "—"}</strong></span></div>{result.evidence?.length > 0 && <button className="text-button" onClick={() => viewEvidence(result.rule_id)}>View evidence ({result.evidence.length})</button>}</article>)}</div>
                {selectedEvidence.length > 0 && <div className="evidence-viewer"><div className="section-heading"><div><p className="eyebrow">EVIDENCE</p><h3>{evidenceRule}</h3></div><button className="text-button" onClick={() => setSelectedEvidence([])}>Close</button></div><div className="evidence-image"><img src={`${API_BASE_URL}/api/v1/inspections/${inspectionId}/image`} alt="Original package evidence" />{selectedEvidence.map((item) => item.bbox?.width > 0 && <div className="evidence-box" key={`${item.evidence_id}-${item.ocr_region_id}`} style={{ left: `${(item.bbox.x / item.image_width) * 100}%`, top: `${(item.bbox.y / item.image_height) * 100}%`, width: `${(item.bbox.width / item.image_width) * 100}%`, height: `${(item.bbox.height / item.image_height) * 100}%` }} />)}</div><div className="evidence-details">{selectedEvidence.map((item) => <div key={`${item.evidence_id}-${item.ocr_region_id}`}><strong>{prettyLabel(item.declaration_type)}</strong><span>{item.value || "Value not confidently extracted"} · {item.source_text || "—"}</span><small>OCR confidence: {item.ocr_confidence != null ? `${(item.ocr_confidence * 100).toFixed(1)}%` : "—"} · Region: {item.ocr_region_id}</small></div>)}</div></div>}
                {compliance && <div className="report-actions"><div><p className="eyebrow">PHASE 9</p><strong>Inspection report</strong>{report && <span className="report-number">{report.report_number}</span>}</div><div className="report-buttons">{!report && <button className="secondary-button" disabled={reportRunning} onClick={generateReport}>{reportRunning ? "Generating PDF…" : "Generate report"}</button>}{report && <button className="secondary-button" onClick={downloadReport}>Download PDF</button>}</div></div>}
              </div>}
            </section>
          </div>
        </section></>}
      </main>
    </div>
  );
}
