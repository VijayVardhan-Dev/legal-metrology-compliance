# Evidence Model

Every compliance decision and violation must be fully traceable to the original source evidence. The system preserves the original uploaded image; AI-generated annotations do not replace original evidence.

## Evidence Traceability Chain
```text
Original Image
      ↓
Detected text/region (via Computer Vision)
      ↓
Bounding box (Coordinates mapping to Original Image)
      ↓
Extracted value (OCR output)
      ↓
Rule (Deterministic evaluation logic)
      ↓
Violation (Resulting assessment)
```

## Storage and Presentation
- **Original Image:** Stored unmodified in object storage. Used as the ground truth.
- **Annotated Image:** Generated dynamically or stored separately for presentation in the UI and PDF reports, displaying bounding boxes over regions of interest.
- **Metadata:** OCR confidence scores, coordinates, and timestamps are stored in the database alongside the violation record.
