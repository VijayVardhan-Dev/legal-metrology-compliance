import { useRef, useState } from 'react';
import { api } from '../services/api';
import { formatPercent } from '../utils/format';
import PageHeader from '../components/ui/PageHeader';
import ErrorBanner from '../components/ui/ErrorBanner';
import StatusBadge from '../components/ui/StatusBadge';

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

function AssessmentBadge({ assessment }) {
  const labels = {
    moderation: 'Moderation',
    additive: 'Additive / functional',
    common: 'Generally acceptable',
    insufficient_information: 'Information insufficient',
  };
  return <StatusBadge status={assessment === 'moderation' ? 'REVIEW_REQUIRED' : assessment === 'insufficient_information' ? 'NOT_APPLICABLE' : 'COMPLIANT'} label={labels[assessment] || assessment} />;
}

function formatAmount(value) {
  const amount = value?.value || 'Not detected';
  const unit = value?.unit && value.unit !== 'Not detected' ? ` ${value.unit}` : '';
  return `${amount}${unit}`;
}

export default function NutritionPage() {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [ocr, setOcr] = useState(null);
  const [error, setError] = useState('');
  const [running, setRunning] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  function chooseFile(nextFile) {
    if (!nextFile) return;
    if (!ACCEPTED_TYPES.includes(nextFile.type)) {
      setError('Please choose a JPG, PNG, or WEBP image.');
      return;
    }
    if (preview) URL.revokeObjectURL(preview);
    setFile(nextFile);
    setPreview(URL.createObjectURL(nextFile));
    setAnalysis(null);
    setOcr(null);
    setError('');
  }

  async function analyze() {
    if (!file) return;
    setRunning(true);
    setError('');
    try {
      const created = await api.createInspection(file);
      const ocrResult = await api.triggerOcr(created.inspection_id);
      setOcr(ocrResult);
      if (ocrResult.status !== 'COMPLETED') {
        throw new Error(ocrResult.error_message || 'OCR could not reliably read this image.');
      }
      setAnalysis(await api.analyzeNutrition(created.inspection_id));
    } catch (requestError) {
      setError(requestError.message || 'Nutrition analysis failed.');
    } finally {
      setRunning(false);
    }
  }

  function clear() {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview('');
    setAnalysis(null);
    setOcr(null);
    setError('');
    if (inputRef.current) inputRef.current.value = '';
  }

  const nutritionRows = Object.entries(analysis?.nutrition || {});

  return (
    <>
      <ErrorBanner error={error} onDismiss={() => setError('')} />
      <PageHeader eyebrow="NUTRITION & INGREDIENTS" title="Nutrition analyzer">
        <span className="text-tertiary">OCR-derived label information</span>
      </PageHeader>

      <section className="card nutrition-upload-card">
        {!file ? (
          <button
            className={`dropzone${dragOver ? ' drag-over' : ''}`}
            type="button"
            onClick={() => inputRef.current?.click()}
            onDragOver={(event) => { event.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(event) => { event.preventDefault(); setDragOver(false); chooseFile(event.dataTransfer.files?.[0]); }}
          >
            <span className="dropzone-icon" aria-hidden="true">↑</span>
            <span className="dropzone-title">Upload a food package image</span>
            <span className="dropzone-hint">Use a clear image of the nutrition and ingredients panel</span>
          </button>
        ) : (
          <div className="upload-preview">
            <img className="upload-preview-image" src={preview} alt="Selected food package" />
            <div className="upload-file-info">
              <strong className="upload-file-name">{file.name}</strong>
              <span className="upload-file-meta">Nutrition analysis uses the existing OCR pipeline.</span>
              <div className="upload-actions">
                <button className="btn" type="button" onClick={clear} disabled={running}>Replace</button>
                <button className="btn btn-primary" type="button" onClick={analyze} disabled={running}>{running ? 'Analyzing…' : 'Analyze nutrition →'}</button>
              </div>
            </div>
          </div>
        )}
        <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={(event) => chooseFile(event.target.files?.[0])} />
      </section>

      {ocr && <section className="card nutrition-status-card">
        <div className="card-header"><div className="card-header-text"><p className="eyebrow">OCR SOURCE</p><h2>Recognition confidence</h2></div><StatusBadge status={ocr.status} /></div>
        <div className="metric-grid"><div><span>Status</span><strong>{ocr.status}</strong></div><div><span>Average confidence</span><strong>{formatPercent(ocr.average_confidence)}</strong></div><div><span>Detected text</span><strong>{ocr.raw_full_text ? `${ocr.raw_full_text.length} characters` : 'Not detected'}</strong></div></div>
      </section>}

      {analysis && <>
        <section className="card nutrition-database-card">
          <div className="card-header"><div className="card-header-text"><p className="eyebrow">PRODUCT DATABASE</p><h2>Open Food Facts verification</h2></div><StatusBadge status={analysis.product_database?.status === 'FOUND' ? 'COMPLETED' : 'NOT_APPLICABLE'} /></div>
          <div className="metric-grid"><div><span>Barcode</span><strong>{analysis.barcode || 'Not detected'}</strong></div><div><span>Database match</span><strong>{analysis.product_database?.status === 'FOUND' ? 'Product found' : analysis.product_database?.status === 'NOT_FOUND' ? 'Product not found' : 'No match'}</strong></div><div><span>Primary source</span><strong>Product label</strong></div></div>
          {analysis.product_database?.status === 'FOUND' && <div className="database-details"><p><strong>{analysis.product_database.product_name || 'Unnamed product'}</strong>{analysis.product_database.brands ? ` · ${analysis.product_database.brands}` : ''}</p><p className="text-secondary">Database source: Open Food Facts{analysis.product_database.serving_size ? ` · Serving: ${analysis.product_database.serving_size}` : ''}{analysis.product_database.quantity ? ` · Quantity: ${analysis.product_database.quantity}` : ''}</p><p className="text-secondary">Nutri-Score: {analysis.product_database.nutri_score || 'Not available'} · NOVA: {analysis.product_database.nova_group || 'Not available'}</p></div>}
          {analysis.product_database?.status === 'FOUND' && <div className="database-details"><p><strong>Database ingredients:</strong> {analysis.product_database.ingredients_text || 'Not available'}</p><p><strong>Database allergens:</strong> {analysis.product_database.allergens?.length ? analysis.product_database.allergens.join(', ') : 'Not available'}</p><p><strong>Database additives:</strong> {analysis.product_database.additives?.length ? analysis.product_database.additives.join(', ') : 'Not available'}</p></div>}
          {analysis.product_database?.status === 'FOUND' && <div className="source-comparison"><strong>Source comparison</strong><span>🏷️ Product label is primary · 🌐 Open Food Facts is supplementary</span>{analysis.source_comparison?.length > 0 && <ul className="nutrition-list">{analysis.source_comparison.map((difference) => <li key={difference.field}>{difference.field}: label {difference.label_value.value} {difference.label_value.unit || ''} vs database {difference.database_value.value} {difference.database_value.unit || ''}</li>)}</ul>}</div>}
        </section>
        {analysis.warnings?.length > 0 && <section className="card nutrition-warning-card"><div className="card-header"><div className="card-header-text"><p className="eyebrow">VERIFY</p><h2>Review the source label</h2></div></div><ul className="nutrition-list">{analysis.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></section>}

        <section className="card">
          <div className="card-header"><div className="card-header-text"><p className="eyebrow">NUTRITION INFORMATION</p><h2>Detected values</h2></div><StatusBadge status={analysis.status} /></div>
          <div className="metric-grid nutrition-confidence-grid"><div><span>Nutrition confidence</span><strong>{formatPercent(analysis.nutrition_confidence)}</strong></div><div><span>Ingredient confidence</span><strong>{formatPercent(analysis.ingredient_confidence)}</strong></div><div><span>Analysis status</span><strong>{analysis.status}</strong></div></div>
          <div className="table-wrap"><table><thead><tr><th>Nutrient</th><th>Amount</th><th>Basis</th><th>Confidence</th></tr></thead><tbody>{nutritionRows.map(([name, value]) => <tr key={name}><td><strong>{name}</strong></td><td>{formatAmount(value)}</td><td>{value.basis || 'Not detected'}</td><td>{formatPercent(value.confidence)}</td></tr>)}</tbody></table></div>
        </section>

        <section className="card">
          <div className="card-header"><div className="card-header-text"><p className="eyebrow">INGREDIENT ANALYSIS</p><h2>What the label contains</h2></div><span className="count-badge">{analysis.ingredients?.length || 0}</span></div>
          <div className="table-wrap"><table><thead><tr><th>Ingredient</th><th>Category</th><th>Purpose</th><th>Assessment</th></tr></thead><tbody>{analysis.ingredients?.length ? analysis.ingredients.map((ingredient, index) => <tr key={`${ingredient.name}-${index}`}><td><strong>{ingredient.name}</strong><small className="table-subtext">Confidence: {formatPercent(ingredient.confidence)}</small></td><td>{ingredient.category}</td><td>{ingredient.purpose}</td><td><AssessmentBadge assessment={ingredient.assessment} /><small className="table-subtext">{ingredient.reason}</small></td></tr>) : <tr><td colSpan="4">Not detected</td></tr>}</tbody></table></div>
        </section>

        {analysis.nlp_analysis && <section className="card"><div className="card-header"><div className="card-header-text"><p className="eyebrow">NLP EXPLANATIONS</p><h2>Ingredient information for users</h2></div><StatusBadge status={analysis.nlp_analysis.status === 'COMPLETED' ? 'COMPLETED' : 'NOT_APPLICABLE'} /></div><p className="text-secondary">{analysis.nlp_analysis.status === 'COMPLETED' ? 'Gemini provided explanations for ingredients already detected by OCR.' : 'Deterministic ingredient explanations are shown. Add GEMINI_API_KEY to enable optional Gemini enrichment.'}</p>{analysis.ingredients?.some((item) => item.consumer_explanation) && <ul className="nutrition-list">{analysis.ingredients.filter((item) => item.consumer_explanation).map((item) => <li key={item.name}><strong>{item.name}:</strong> {item.consumer_explanation}</li>)}</ul>}</section>}

        <div className="grid-2">
          <section className="card"><div className="card-header"><div className="card-header-text"><p className="eyebrow">ALLERGENS</p><h2>Declared allergens</h2></div></div>{analysis.allergens?.length ? <><p className="allergen-alert">Allergens detected</p><ul className="nutrition-list">{analysis.allergens.map((allergen) => <li key={allergen.name}>{allergen.name} <span className="table-subtext">({formatPercent(allergen.confidence)})</span></li>)}</ul></> : <p className="text-secondary">No allergens were explicitly detected in the extracted text.</p>}</section>
          <section className="card"><div className="card-header"><div className="card-header-text"><p className="eyebrow">CONSUMER INSIGHTS</p><h2>Label observations</h2></div></div><ul className="nutrition-list">{(analysis.insights || ['Unable to determine from the available label information.']).map((insight) => <li key={insight}>{insight}</li>)}</ul></section>
        </div>

        <section className="card"><div className="card-header"><div className="card-header-text"><p className="eyebrow">RAW DETECTED INGREDIENT LIST</p><h2>OCR source text</h2></div></div><p className="raw-label-text">{analysis.ingredient_text || 'Not detected'}</p></section>
        <section className="card"><div className="card-header"><div className="card-header-text"><p className="eyebrow">FOOD SUITABILITY</p><h2>{analysis.suitability?.status || 'INSUFFICIENT_INFORMATION'}</h2></div></div><p className="text-secondary">{analysis.suitability?.reason || 'Unable to determine from the available information.'}</p></section>
      </>}
    </>
  );
}
