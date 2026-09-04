# System Architecture

## Architecture Flow (Separation of AI and Legal Decision-Making)

The AI system is strictly responsible for extracting data ("What information appears on the package?"). The Rule Engine evaluates that data ("Does the extracted information satisfy the applicable rule?"). An LLM does NOT directly decide legal compliance.

```text
Product Image
      ↓
Image Processing (OpenCV)
      ↓
OCR / Computer Vision (PaddleOCR, YOLO)
      ↓
Extracted Evidence (Bounding boxes, confidence scores)
      ↓
Structured Declarations (JSON representing extracted text)
      ↓
Rule Engine (Custom Python deterministic logic)
      ↓
Compliance Assessment (COMPLIANT / NON_COMPLIANT / REVIEW_REQUIRED)
```

## User Workflow
```text
Login
 ↓
Dashboard
 ↓
Create Inspection
 ↓
Upload / Capture Product Images
 ↓
Select Product Category
 ↓
Analyze
 ↓
OCR + AI Processing
 ↓
Declaration Extraction
 ↓
Rule Validation
 ↓
Compliance Result
 ↓
Review Violations
 ↓
View Evidence
 ↓
Officer Verification
 ↓
Generate Report
 ↓
Store Inspection History
```

## Technology Stack (Planned)
- **Frontend:** React + JavaScript, Tailwind CSS
- **Backend:** Python + FastAPI
- **OCR:** PaddleOCR
- **Computer Vision:** OpenCV (YOLO later if required for component detection)
- **Database:** PostgreSQL
- **Object Storage:** MinIO (for images and reports)
- **Reports:** ReportLab (PDF generation)
- **Authentication:** JWT + Role-Based Access Control (RBAC)
- **Deployment:** Docker + Nginx
