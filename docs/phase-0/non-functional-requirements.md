# Non-Functional Requirements

## Performance
- The system must provide reasonable response times (e.g., under 15 seconds) for processing normal package images and generating compliance assessments.

## Security
- Implement secure JWT-based Authentication and RBAC Authorization.
- Secure file handling for image uploads (sanitization, virus scanning if applicable).
- No hardcoded secrets or credentials in the source code.
- Implement strict input validation for all API endpoints.

## Reliability
- AI failure (e.g., OCR timeout, image unreadable) must fail gracefully and not crash the inspection system. Such failures should result in a `REVIEW_REQUIRED` state.

## Auditability
- Every compliance decision must be fully traceable. The chain `Image → extracted data → rule → result` must be preserved in the database for auditing purposes.

## Scalability
- The architecture must be modular, particularly the Rule Engine. It should allow additional product categories and rules to be added as JSON configurations or modular Python functions without rewriting the core application logic.

## AI Confidence Handling
- The system handles confidence via thresholds:
  - **HIGH CONFIDENCE:** > 0.85 (Proceeds to rule validation)
  - **MEDIUM CONFIDENCE:** 0.60 - 0.85 (May trigger REVIEW_REQUIRED depending on the rule)
  - **LOW CONFIDENCE:** < 0.60 (Automatically triggers REVIEW_REQUIRED)
- *Important:* A low-confidence extraction must not automatically result in a legal violation, but rather flags the item for manual officer review.
- Compliance Score, if used, is strictly an **application-level screening score** (e.g., "7/8 mandatory checks passed"), not a legal percentage of compliance.
