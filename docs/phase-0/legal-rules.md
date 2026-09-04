# Legal Rules Specification

This specifies the structured requirements the software will implement, based on the Legal Metrology (Packaged Commodities) Rules, 2011.

## Rule ID: MRP-001
- **Rule reference:** Rule 6(1)(e)
- **Requirement:** Retail sale price must be declared as "Maximum Retail Price Rs. XX.XX (inclusive of all taxes)" or "MRP Rs. XX.XX (incl., of all taxes)".
- **Applicable product category:** All packaged commodities for retail sale.
- **Input required:** OCR text + image region.
- **Validation logic:** Regex/pattern match for "MRP" / "Maximum Retail Price" followed by currency symbol/text and numeric value.
- **Pass condition:** Valid MRP format and value detected.
- **Fail condition:** No MRP detected, or format clearly violates standard (e.g., missing "incl. of all taxes").
- **Unable-to-determine condition:** Text is blurry, partially visible, or OCR confidence is low.
- **Severity:** HIGH
- **Explanation shown to inspector:** "Maximum Retail Price declaration must be present and formatted correctly."
- **Evidence required:** Original image + bounding box around detected MRP text.

## Rule ID: NETQTY-001
- **Rule reference:** Rule 6(1)(c) & Rule 13
- **Requirement:** Net quantity must be declared in standard units of weight, measure, or number.
- **Applicable product category:** All packaged commodities.
- **Input required:** OCR text + image region.
- **Validation logic:** Extract value and unit. Verify unit is standard (e.g., g, kg, ml, L).
- **Pass condition:** Valid net quantity detected with standard units.
- **Fail condition:** Declaration missing or uses non-standard units.
- **Unable-to-determine condition:** Text illegible or OCR confidence low.
- **Severity:** HIGH
- **Explanation shown to inspector:** "Net quantity must be declared using standard metric units."
- **Evidence required:** Original image + bounding box around detected quantity text.

*(More rules will be added following this structure during implementation.)*
