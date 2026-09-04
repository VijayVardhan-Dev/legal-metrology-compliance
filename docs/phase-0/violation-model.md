# Violation Model

Violations are structured using a standard schema to ensure consistency and traceability.

## Structure
- **Violation ID:** Unique identifier for the violation record.
- **Inspection ID:** Link to the parent inspection.
- **Rule ID:** The specific legal rule evaluated (e.g., NETQTY-001).
- **Field:** The declaration field in question (e.g., `net_quantity`).
- **Status:** FAIL or REVIEW_REQUIRED.
- **Severity:** HIGH, MEDIUM, LOW.
- **Description:** Human-readable explanation of the issue.
- **Detected value:** The actual text/value extracted by OCR.
- **Expected requirement:** The legally required format or presence.
- **Confidence:** AI/OCR confidence score (0.0 to 1.0).
- **Evidence image:** Link/reference to the annotated image.
- **Bounding box:** Coordinates `[x1, y1, x2, y2]` of the region on the original image.
- **Requires officer verification:** Boolean flag (True for most violations).

## Example
```json
{
  "violation_id": "v_12345",
  "inspection_id": "insp_9988",
  "rule_id": "NETQTY-001",
  "field": "net_quantity",
  "status": "FAIL",
  "severity": "HIGH",
  "description": "Declaration does not satisfy the applicable requirement. Non-standard unit used.",
  "detected_value": "500 ounces",
  "expected_requirement": "Metric units (e.g., g, kg)",
  "confidence": 0.94,
  "evidence_image": "bucket/inspections/insp_9988/box_2.jpg",
  "bounding_box": [150, 300, 250, 340],
  "requires_officer_verification": true
}
```
