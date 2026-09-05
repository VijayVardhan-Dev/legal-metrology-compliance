import { useMemo, useRef, useState } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const STEPS = [["upload", "Upload"], ["ocr", "OCR"], ["declarations", "Declarations"], ["category", "Category"], ["compliance", "Compliance"]];

function statusClass(status) {
  return {
    COMPLIANT: "status status-green",
    NON_COMPLIANT: "status status-red",
    REVIEW_REQUIRED: "status status-yellow",
    FOUND: "status status-green",
    INCOMPLETE: "status status-yellow",
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
  const [compliance, setCompliance] = useState(null);
  const [activeStep, setActiveStep] = useState("upload");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

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
    ...(compliance ? ["compliance"] : []),
  ]), [inspectionId, ocr, declarations, category, compliance]);

  function chooseFile(nextFile) {
    if (!nextFile || !nextFile.type.startsWith("image/")) {
      setError("Please choose a supported image file.");
      return;
    }
    setFile(nextFile);
    setPreview(URL.createObjectURL(nextFile));
    setError("");
    setInspectionId(""); setOcr(null); setDeclarations([]); setCategory(null); setCompliance(null); setActiveStep("upload");
  }

  function reset() {
    setFile(null); setPreview(""); setInspectionId(""); setOcr(null); setDeclarations([]); setCategory(null); setCompliance(null);
    setActiveStep("upload"); setError("");
    if (inputRef.current) inputRef.current.value = "";
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
      const categoryResult = await request(`/api/v1/inspections/${created.inspection_id}/category`, { method: "POST" });
      setCategory(categoryResult); setActiveStep("compliance");
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
        <div className="api-indicator"><span /> API {API_BASE_URL}</div>
        <button className="logout-button" onClick={logout}>Sign out</button>
      </header>
      <main className="page">
        <section className="hero">
          <div><p className="eyebrow">PHASE 1–6 TESTING FRONTEND</p><h2>Inspect a package label end to end.</h2><p className="hero-copy">Upload one package image to run OCR, declaration extraction, and deterministic compliance evaluation in sequence.</p></div>
          {inspectionId && <div className="inspection-chip">Inspection <strong>{inspectionId.slice(0, 8)}…</strong></div>}
        </section>
        <section className="stepper card">
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
            <section className="card">
              <div className="section-heading"><div><p className="eyebrow">PHASE 6</p><h3>Compliance summary</h3></div>{compliance?.overall_status && <span className={statusClass(compliance.overall_status)}>{compliance.overall_status}</span>}</div>
              {!compliance ? <div className="empty-state">Rule evaluation will appear here after declarations are stored.</div> : <div className="rule-list">{(compliance.results || []).map((result) => <article className="rule-card" key={result.rule_id}><div className="rule-top"><div><strong>{result.rule_id}</strong><span className="legal-reference">{result.legal_reference}</span></div><span className={statusClass(result.status)}>{result.status}</span></div><p>{result.reason}</p><div className="rule-meta"><span>Severity: <strong>{result.severity}</strong></span>{result.evidence?.length > 0 && <span>Evidence: <strong>{result.evidence.length} item{result.evidence.length === 1 ? "" : "s"}</strong></span>}</div>{result.evidence?.length > 0 && <details><summary>View evidence</summary><pre>{JSON.stringify(result.evidence, null, 2)}</pre></details>}</article>)}</div>}
            </section>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
