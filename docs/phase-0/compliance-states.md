# Compliance States

The system produces exactly three possible compliance states for any product or individual rule evaluation.

## 1. COMPLIANT
All automated checks passed with sufficient confidence. The extracted declarations meet the deterministic rule requirements.

## 2. NON_COMPLIANT
One or more applicable checks failed with sufficient evidence. Examples include a definitively missing MRP or a net quantity declared in illegal units.

## 3. REVIEW_REQUIRED
The system cannot reliably determine compliance. This state is triggered by:
- Poor image quality or blur
- Missing package sides (e.g., front submitted, but rules require back panel info)
- Low OCR uncertainty (confidence below threshold)
- Insufficient physical scale to determine font size
- Ambiguous declarations
- Product-category uncertainty
- Legal conditions requiring human interpretation (e.g., specific exemptions)

*Note: Uncertain cases are never forced into PASS or FAIL.*
