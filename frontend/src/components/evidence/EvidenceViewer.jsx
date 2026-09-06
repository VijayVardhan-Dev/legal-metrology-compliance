import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../../services/api';
import { formatPercent } from '../../utils/format';

export default function EvidenceViewer({ inspectionId, ruleId, items, onClose }) {
  const panelRef = useRef(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragging = useRef(false);
  const lastPos = useRef({ x: 0, y: 0 });

  // Close on Escape
  useEffect(() => {
    function handleKey(e) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  // Prevent body scroll
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  const handleWheel = useCallback((e) => {
    e.preventDefault();
    setZoom((prev) => Math.min(5, Math.max(0.5, prev + (e.deltaY < 0 ? 0.2 : -0.2))));
  }, []);

  function handleMouseDown(e) {
    if (zoom <= 1) return;
    dragging.current = true;
    lastPos.current = { x: e.clientX, y: e.clientY };
  }

  function handleMouseMove(e) {
    if (!dragging.current) return;
    setPan((prev) => ({
      x: prev.x + (e.clientX - lastPos.current.x),
      y: prev.y + (e.clientY - lastPos.current.y),
    }));
    lastPos.current = { x: e.clientX, y: e.clientY };
  }

  function handleMouseUp() {
    dragging.current = false;
  }

  function resetView() {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }

  return (
    <div
      className="evidence-overlay"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      role="dialog"
      aria-modal="true"
      aria-label={`Evidence for ${ruleId}`}
    >
      <div className="evidence-panel" ref={panelRef}>
        <div className="evidence-panel-header">
          <div>
            <p className="eyebrow">EVIDENCE VIEWER</p>
            <h2>{ruleId}</h2>
          </div>
          <div className="card-actions">
            {zoom !== 1 && (
              <button className="btn btn-sm" onClick={resetView}>
                Reset zoom
              </button>
            )}
            <button className="btn btn-sm" onClick={onClose} aria-label="Close evidence viewer">
              ✕ Close
            </button>
          </div>
        </div>

        <div className="evidence-panel-body">
          {items.map((item, i) => (
            <div className="evidence-item" key={`${item.evidence_id}-${i}`}>
              <div
                className="evidence-image-container"
                onWheel={handleWheel}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
              >
                <img
                  src={api.imageUrl(inspectionId)}
                  alt="Package with evidence highlight"
                  style={{
                    transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`,
                  }}
                  draggable={false}
                />
                {item.bbox && item.image_width > 0 && (
                  <span
                    className="evidence-bbox"
                    style={{
                      left: `${(item.bbox.x / item.image_width) * 100}%`,
                      top: `${(item.bbox.y / item.image_height) * 100}%`,
                      width: `${(item.bbox.width / item.image_width) * 100}%`,
                      height: `${(item.bbox.height / item.image_height) * 100}%`,
                    }}
                    aria-label={`Bounding box for ${item.value || 'detected text'}`}
                  />
                )}
              </div>

              <div className="evidence-details">
                <span className="evidence-value">
                  {item.value || 'Detected text'}
                </span>
                <p className="evidence-source">
                  {item.source_text || 'No source text returned.'}
                </p>
                <span className="evidence-meta">
                  OCR confidence: {formatPercent(item.ocr_confidence)}
                  {item.legal_reference && ` · ${item.legal_reference}`}
                </span>
                {item.reason && (
                  <p className="evidence-reason">{item.reason}</p>
                )}
                {item.declaration_type && (
                  <span className="text-tertiary">
                    Declaration: {item.declaration_type}
                  </span>
                )}
              </div>
            </div>
          ))}

          {items.length === 0 && (
            <div className="empty-state">
              No evidence data available for this rule.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
