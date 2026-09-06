import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { formatFileSize } from '../utils/format';
import PageHeader from '../components/ui/PageHeader';
import ErrorBanner from '../components/ui/ErrorBanner';

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export default function NewInspectionPage() {
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState('');
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  function chooseFile(f) {
    if (!f) return;
    if (!ACCEPTED_TYPES.includes(f.type)) {
      setError('Please choose a JPG, PNG, or WEBP image.');
      return;
    }
    setError('');
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }

  function clearFile() {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview('');
    setError('');
  }

  async function startAnalysis() {
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const result = await api.createInspection(file);
      navigate(`/inspections/${result.inspection_id}?run=1`);
    } catch (e) {
      setError(e.message);
      setUploading(false);
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    chooseFile(e.dataTransfer.files[0]);
  }

  return (
    <>
      <ErrorBanner error={error} onDismiss={() => setError('')} />

      <PageHeader eyebrow="NEW INSPECTION" title="Upload package">
        <span className="text-tertiary">AI-assisted compliance screening</span>
      </PageHeader>

      <section className="card upload-container">
        {!file ? (
          <button
            className={`dropzone${dragOver ? ' drag-over' : ''}`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            type="button"
            aria-label="Upload package image"
          >
            <div className="dropzone-icon" aria-hidden="true">↑</div>
            <span className="dropzone-title">Drop a package image here</span>
            <span className="dropzone-hint">or choose a file · JPG, PNG, WEBP</span>
          </button>
        ) : (
          <div className="upload-preview">
            <img
              className="upload-preview-image"
              src={preview}
              alt="Selected package"
            />
            <div className="upload-file-info">
              <span className="upload-file-name">{file.name}</span>
              <span className="upload-file-meta">
                {formatFileSize(file.size)} · {file.type.split('/')[1].toUpperCase()}
              </span>
              <div className="upload-actions">
                <button
                  className="btn"
                  onClick={clearFile}
                  disabled={uploading}
                >
                  Replace
                </button>
                <button
                  className="btn btn-primary"
                  onClick={startAnalysis}
                  disabled={uploading}
                >
                  {uploading ? 'Uploading…' : 'Start analysis →'}
                </button>
              </div>
            </div>
          </div>
        )}

        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          hidden
          onChange={(e) => chooseFile(e.target.files?.[0])}
        />
      </section>
    </>
  );
}
