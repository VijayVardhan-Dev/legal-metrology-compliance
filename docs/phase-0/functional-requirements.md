# Functional Requirements

## Authentication
- Login and Logout functionality.
- Role-based access control (RBAC): Inspector, Senior Officer, Administrator.

## Inspection Workflow
- Create a new inspection record.
- Upload/capture product images (front, back, sides).
- Add product information and select product category.
- Trigger AI analysis.
- Review results and manual override/verification.

## AI Processing
- Image preprocessing (deskew, contrast enhancement).
- OCR for text extraction.
- Declaration categorization and extraction.
- Provision of confidence scores and bounding boxes.

## Compliance Engine
- Select applicable rules based on product category.
- Validate extracted declarations against rules.
- Detect missing mandatory information.
- Return compliance status (COMPLIANT, NON_COMPLIANT, REVIEW_REQUIRED).

## Evidence Handling
- Store original images securely.
- Generate and display annotated images with violation regions.
- Link supporting evidence to specific rules/violations.

## Reports
- Generate official PDF inspection reports.
- Include inspection details, extracted declarations, detected violations, visual evidence, rule references, and officer signature/details.

## Repository & Search
- Store product and inspection histories.
- Search past inspections by product name, date, or status.
- Filter results and retrieve previous PDF reports.

## Dashboard
- Display metrics: Total inspections, Compliant, Non-compliant, Review required.
- Show violation statistics (e.g., most common violations).
- Provide date and category filters.
