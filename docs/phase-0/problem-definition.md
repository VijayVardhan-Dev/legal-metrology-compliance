# Problem Definition

## The Problem
Legal Metrology enforcement officials are responsible for ensuring that packaged commodities comply with the Legal Metrology (Packaged Commodities) Rules, 2011. This involves verifying numerous mandatory declarations on millions of products.

## Why Manual Inspection is Difficult
Doing this manually for hundreds or thousands of products is slow, inconsistent, and highly labor-intensive. An officer must visually scan the package, locate each mandatory declaration, assess its formatting, check its validity, and manually record any violations.

## Information to be Checked
Key declarations include:
- Product name
- Manufacturer/packer/importer details and address
- Net quantity
- Maximum Retail Price (MRP)
- Manufacturing/packing/import dates
- Consumer-care/contact details

## How the System Improves the Workflow
The system acts as an **AI-assisted compliance screening system**. By uploading a photo of a packaged product, the system automatically reads the label, extracts the declarations, checks them against encoded rules, and flags potential violations with visual evidence. This allows officers to inspect more products in less time and standardizes the inspection process.

## System Capabilities and Limitations
**What it CAN do:**
- Extract text from images using OCR.
- Detect the presence or absence of mandatory declarations.
- Verify if extracted data matches required formats (e.g., date formats, MRP formats).
- Highlight potential violations with bounding boxes and evidence.

**What it CANNOT do:**
- Determine compliance with 100% accuracy in ambiguous cases.
- Perfectly measure physical font sizes from uncalibrated photographs.
- Replace an authorized Legal Metrology officer. The system provides evidence-based screening; final legal decisions and enforcement actions require officer verification.
