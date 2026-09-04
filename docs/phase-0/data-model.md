# Data Model Requirements

The database structure relies on the following core entities and their relationships.

## Entities
1. **User:** System users (Inspectors, Senior Officers, Administrators).
2. **Product:** A distinct packaged commodity (e.g., "XYZ Shampoo 200ml").
3. **Inspection:** A single inspection event performed by a user on a product.
4. **Declaration:** Extracted data points from an inspection (e.g., the extracted MRP).
5. **Rule:** Encoded legal requirements.
6. **Violation:** A rule failure or review request associated with an inspection.
7. **Evidence:** Image references and bounding boxes associated with declarations and violations.
8. **Report:** Generated summary document for an inspection.

## Relationships
- A `User` performs many `Inspection`s.
- An `Inspection` belongs to one `Product`.
- An `Inspection` has many `Declaration`s, `Violation`s, and `Evidence` records.
- An `Inspection` has one generated `Report`.
- A `Violation` references one `Rule` and one or more pieces of `Evidence`.
