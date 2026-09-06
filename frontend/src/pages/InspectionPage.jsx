import { useState, useEffect, useCallback, Fragment } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { api, poll } from '../services/api';
import { formatPercent, prettify } from '../utils/format';
import PageHeader from '../components/ui/PageHeader';
import StatusBadge from '../components/ui/StatusBadge';
import EmptyState from '../components/ui/EmptyState';
import ErrorBanner from '../components/ui/ErrorBanner';
import { SkeletonCard } from '../components/ui/Skeleton';
import EvidenceViewer from '../components/evidence/EvidenceViewer';

const STEPS = [
  ['upload', 'Upload'],
  ['ocr', 'OCR'],
  ['declarations', 'Declarations'],
  ['category', 'Category'],
  ['visual', 'Visual analysis'],
  ['compliance', 'Compliance'],
  ['complete', 'Complete'],
];

export default function InspectionPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const shouldRun = searchParams.get('run') === '1';
  const navigate = useNavigate();

  const [state, setState] = useState({});
  const [processing, setProcessing] = useState(shouldRun);
  const [error, setError] = useState('');
  const [evidence, setEvidence] = useState(null);

  const update = useCallback((key, value) => {
    setState((prev) => ({ ...prev, [key]: value }));
  }, []);

  // Main analysis workflow
  useEffect(() => {
    let cancelled = false;

    async function runWorkflow() {
      try {
        // Always fetch inspection detail
        const detail = await api.getInspection(id);
        if (cancelled) return;
        update('detail', detail);

        if (!shouldRun) {
          // Just viewing — fetch existing data
          const results = await Promise.allSettled([
            api.getOcr(id),
            api.getDeclarations(id),
            api.getCategory(id),
            api.getVisual(id),
            api.getCompliance(id),
          ]);
          const keys = ['ocr', 'declarations', 'category', 'visual', 'compliance'];
          results.forEach((r, i) => {
            if (!cancelled && r.status === 'fulfilled') update(keys[i], r.value);
          });
          return;
        }

        // Run the full pipeline
        // 1. OCR
        const ocrInitial = await api.triggerOcr(id);
        if (cancelled) return;
        update('ocr', ocrInitial);

        const ocrFinal = ['PROCESSING', 'PENDING'].includes(ocrInitial.status)
          ? await poll(() => api.getOcr(id), (r) => ['COMPLETED', 'FAILED'].includes(r.status))
          : ocrInitial;
        if (cancelled) return;
        update('ocr', ocrFinal);

        if (ocrFinal.status !== 'COMPLETED') {
          throw new Error(ocrFinal.error_message || 'OCR processing failed.');
        }

        // 2. Declarations
        const declarations = await api.triggerDeclarations(id);
        if (cancelled) return;
        update('declarations', declarations);

        // 3. Category + Visual (parallel)
        const [category, visualInitial] = await Promise.all([
          api.triggerCategory(id),
          api.triggerVisual(id),
        ]);
        if (cancelled) return;
        update('category', category);
        update('visual', visualInitial);

        // Poll visual if needed
        const visualFinal = ['PROCESSING', 'PENDING'].includes(visualInitial?.processing_status)
          ? await poll(
              () => api.getVisual(id),
              (r) => !['PROCESSING', 'PENDING'].includes(r.processing_status)
            )
          : visualInitial;
        if (cancelled) return;
        update('visual', visualFinal);

        // 4. Compliance
        const compliance = await api.triggerCompliance(id);
        if (cancelled) return;
        update('compliance', compliance);
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setProcessing(false);
      }
    }

    runWorkflow();
    return () => { cancelled = true; };
  }, [id, shouldRun, update]);

  // Determine current step
  const currentStep = state.compliance
    ? 'complete'
    : state.visual
      ? 'compliance'
      : state.category
        ? 'visual'
        : state.declarations
          ? 'category'
          : state.ocr
            ? 'declarations'
            : 'ocr';
  const currentIndex = STEPS.findIndex(([key]) => key === currentStep);

  // Evidence handler
  async function showEvidence(ruleId) {
    try {
      const items = await api.getEvidence(id, { rule: ruleId });
      setEvidence({ rule: ruleId, items });
    } catch (e) {
      setError(e.message);
    }
  }

  // Report generation
  async function generateReport() {
    try {
      const report = await api.generateReport(id);
      update('report', report);
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <>
      <ErrorBanner error={error} onDismiss={() => setError('')} />

      <PageHeader
        eyebrow="INSPECTION"
        title={state.detail?.product?.name || 'Inspection'}
      >
        <button className="btn" onClick={() => navigate('/inspections')}>
          ← Back to history
        </button>
      </PageHeader>

      {/* Step indicator */}
      <div className="step-indicator" role="progressbar" aria-label="Analysis progress">
        {STEPS.map(([key, label], i) => {
          const isDone = i < currentIndex || (key === 'complete' && state.compliance);
          const isCurrent = i === currentIndex && processing;
          return (
            <Fragment key={key}>
              {i > 0 && (
                <span
                  className={`step-connector${isDone ? ' step-connector-done' : ''}`}
                />
              )}
              <span
                className={`step-item${isDone ? ' step-done' : ''}${isCurrent ? ' step-current' : ''}`}
              >
                <span className="step-number">{isDone ? '✓' : i + 1}</span>
                {label}
              </span>
            </Fragment>
          );
        })}
      </div>

      {/* Processing indicator */}
      {processing && (
        <div className="processing-card card">
          <div className="processing-spinner" />
          <div className="processing-text">
            <strong>Processing package evidence</strong>
            <span>Each stage appears when the backend completes it. No progress is estimated.</span>
          </div>
        </div>
      )}

      {/* Package image + Declarations */}
      <div className="grid-2">
        <section className="card">
          <div className="card-header">
            <div className="card-header-text">
              <p className="eyebrow">PACKAGE</p>
              <h2>Original image</h2>
            </div>
          </div>
          <img
            className="package-image"
            src={api.imageUrl(id)}
            alt="Uploaded package"
          />
          <div className="image-meta">
            <span>
              Dimensions: {state.ocr?.image_width || '—'} × {state.ocr?.image_height || '—'}
            </span>
            <span>OCR confidence: {formatPercent(state.ocr?.average_confidence)}</span>
          </div>
        </section>

        <section className="card">
          <div className="card-header">
            <div className="card-header-text">
              <p className="eyebrow">DETECTED DECLARATIONS</p>
              <h2>Label data</h2>
            </div>
          </div>
          <DeclarationTable items={state.declarations?.declarations || []} />
        </section>
      </div>

      {/* Category & Visual info */}
      {(state.category || state.visual) && (
        <div className="grid-2">
          {state.category && (
            <section className="card">
              <div className="card-header">
                <div className="card-header-text">
                  <p className="eyebrow">CLASSIFICATION</p>
                  <h2>Product category</h2>
                </div>
                <StatusBadge status={state.category.status} />
              </div>
              <div className="category-list">
                <div className="category-item">
                  <span className="category-name">Category</span>
                  <span className="category-count">{prettify(state.category.category)}</span>
                </div>
                {state.category.subcategory && (
                  <div className="category-item">
                    <span className="category-name">Subcategory</span>
                    <span className="category-count">{prettify(state.category.subcategory)}</span>
                  </div>
                )}
                <div className="category-item">
                  <span className="category-name">Confidence</span>
                  <span className="category-count confidence">{formatPercent(state.category.confidence)}</span>
                </div>
              </div>
            </section>
          )}

          {state.visual && (
            <section className="card">
              <div className="card-header">
                <div className="card-header-text">
                  <p className="eyebrow">VISUAL ANALYSIS</p>
                  <h2>Image quality</h2>
                </div>
                <StatusBadge status={state.visual.quality_status} />
              </div>
              <div className="category-list">
                <div className="category-item">
                  <span className="category-name">Quality score</span>
                  <span className="category-count confidence">{formatPercent(state.visual.quality_score)}</span>
                </div>
                <div className="category-item">
                  <span className="category-name">Dimensions</span>
                  <span className="category-count">
                    {state.visual.image_width || '—'} × {state.visual.image_height || '—'}
                  </span>
                </div>
                {state.visual.findings?.length > 0 && (
                  <div className="category-item">
                    <span className="category-name">Findings</span>
                    <span className="category-count">{state.visual.findings.length}</span>
                  </div>
                )}
              </div>
            </section>
          )}
        </div>
      )}

      {/* Compliance results */}
      {state.compliance && (
        <section className="card">
          <div className="card-header">
            <div className="card-header-text">
              <p className="eyebrow">COMPLIANCE</p>
              <h2>Applicable rules</h2>
            </div>
            <div className="card-actions">
              <StatusBadge status={state.compliance.overall_status} />
              {state.report ? (
                <a
                  className="btn btn-sm"
                  href={api.reportDownloadUrl(id)}
                  target="_blank"
                  rel="noreferrer"
                >
                  Download report
                </a>
              ) : (
                <button className="btn btn-primary btn-sm" onClick={generateReport}>
                  Generate report
                </button>
              )}
            </div>
          </div>

          <div className="compliance-summary">
            <span className="compliance-summary-score">
              {formatPercent(state.compliance.overall_confidence)}
            </span>
            <span className="compliance-summary-detail">
              overall confidence · {state.compliance.total_rules} rules evaluated
            </span>
          </div>

          <RuleTable
            items={state.compliance.results || []}
            onEvidence={showEvidence}
          />
        </section>
      )}

      {/* Evidence viewer */}
      {evidence && (
        <EvidenceViewer
          inspectionId={id}
          ruleId={evidence.rule}
          items={evidence.items}
          onClose={() => setEvidence(null)}
        />
      )}
    </>
  );
}

// --- Declaration Table ---------------------------------------------------
function DeclarationTable({ items }) {
  if (!items.length) {
    return <EmptyState>Declarations will appear after OCR.</EmptyState>;
  }

  return (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>Declaration</th>
            <th>Value</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {items.map((d) => (
            <tr key={d.id}>
              <td>
                <span className="cell-primary">
                  {prettify(d.field_name || d.declaration_type)}
                </span>
                <span className="cell-secondary">{d.source_text}</span>
              </td>
              <td>{d.value || '—'} {d.unit || ''}</td>
              <td className="confidence">{formatPercent(d.confidence)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --- Rule Table ----------------------------------------------------------
function RuleTable({ items, onEvidence }) {
  if (!items.length) {
    return <EmptyState>No rules evaluated.</EmptyState>;
  }

  return (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>Rule</th>
            <th>Status</th>
            <th>Finding</th>
            <th>Evidence</th>
          </tr>
        </thead>
        <tbody>
          {items.map((r) => (
            <tr key={r.id}>
              <td>
                <span className="cell-primary">{r.rule_id}</span>
                <span className="cell-secondary">{r.rule_name}</span>
              </td>
              <td><StatusBadge status={r.status} /></td>
              <td>{r.reason}</td>
              <td>
                <button className="btn-link" onClick={() => onEvidence(r.rule_id)}>
                  View
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
