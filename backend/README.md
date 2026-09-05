# Backend — Phase 2

## Legal Metrology Compliance API

FastAPI backend with PostgreSQL integration for the AI-powered Legal Metrology Compliance Checker.

### Prerequisites

- Python 3.11+
- PostgreSQL running locally

### PostgreSQL Setup

```bash
# 1. Create the database (psql or pgAdmin)
CREATE DATABASE legal_metrology;

# 2. Copy and edit environment config
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux

# 3. Set your DATABASE_URL in .env
# If your password has special chars (@ → %40), URL-encode them:
DATABASE_URL=postgresql+psycopg://postgres:yourpassword@localhost:5432/legal_metrology
```

### Quick Start

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run database migrations
alembic upgrade head

# 4. Run the server
uvicorn app.main:app --reload

# 5. Run tests
pytest tests/ -v
```

### Endpoints

| Method | Path                                   | Description                         |
|--------|----------------------------------------|-------------------------------------|
| GET    | `/api/v1/health`                       | Service health                      |
| POST   | `/api/v1/inspections`                  | Upload image & create inspection    |
| GET    | `/api/v1/inspections/{id}`             | Retrieve inspection details         |
| GET    | `/api/v1/inspections/{id}/image`       | Retrieve uploaded image             |
| POST | `/api/v1/inspections/{id}/visual-analysis` | Analyze image quality and declaration visibility |
| GET  | `/api/v1/inspections/{id}/visual-analysis` | Retrieve visual analysis results |
| POST | `/api/v1/inspections/{id}/compliance` | Evaluate traceable compliance results |
| GET  | `/api/v1/inspections/{id}/compliance` | Retrieve compliance summary and rule results |
| GET  | `/api/v1/inspections/{id}/evidence` | Retrieve original-image evidence, optionally filtered by `rule`, `declaration`, or `evidence_type` |
| POST | `/api/v1/inspections/{id}/report` | Generate an evidence-backed PDF inspection report |
| GET  | `/api/v1/inspections/{id}/report` | Retrieve latest report metadata |
| GET  | `/api/v1/inspections/{id}/report/download` | Download the latest generated PDF report |
| GET | `/api/v1/inspections` | Paginated inspection history with filters and safe sorting |
| GET | `/api/v1/dashboard/summary` | Aggregated inspection/compliance summary |
| GET | `/api/v1/dashboard/compliance-distribution` | Compliance status counts |
| GET | `/api/v1/dashboard/category-distribution` | Category and subcategory counts |
| GET | `/api/v1/dashboard/rules` | Rule-level evaluation statistics |
| GET | `/api/v1/dashboard/recent-inspections` | Most recent concise inspection summaries |

Inspection history accepts `page` (default 1), `page_size` (default 20, maximum
100), `status`, `compliance_status`, `category`, `subcategory`, `product_name`,
`report_number`, `search`, `minimum_confidence`, `maximum_confidence`,
`date_from`, `date_to`, `sort_by`, and `sort_order`. Dates are inclusive ISO
8601 timestamps. Supported sort fields are `created_at`, `updated_at`,
`overall_confidence`, `product_name`, and `compliance_status`.

Dashboard endpoints accept inclusive ISO 8601 `date_from`/`date_to` filters and
an optional `category`. They aggregate persisted `compliance_runs` and
`rule_results`; inspections without a completed compliance run are counted
separately and are never treated as compliant.

### API Docs

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

### Database Schema

| Table          | Description                             |
|----------------|-----------------------------------------|
| users          | System users (inspectors, officers)     |
| products       | Packaged commodities                    |
| inspections    | Inspection events                       |
| declarations   | Extracted label data per inspection     |
| rules          | Legal Metrology rule definitions        |
| violations     | Rule failures per inspection            |
| evidence       | Image files and bounding boxes          |
| reports        | Generated PDF reports per inspection    |
| visual_analyses | Image quality, OCR-region visibility, and visual evidence |
| compliance_runs | Idempotent inspection-level compliance summaries and evaluation metadata |

### Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── api/
│   │   ├── __init__.py
│   │   └── health.py        # Health check endpoint
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Environment-based configuration
│   │   └── database.py      # SQLAlchemy engine + session
│   ├── models/
│   │   ├── __init__.py      # Central model imports
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── inspection.py
│   │   ├── declaration.py
│   │   ├── rule.py
│   │   ├── violation.py
│   │   ├── evidence.py
│   │   └── report.py
│   ├── schemas/              # Pydantic schemas (Phase 3+)
│   └── services/             # Business logic (Phase 3+)
├── alembic/
│   ├── env.py
│   └── versions/
├── tests/
│   ├── test_health.py
│   └── test_database.py
├── .env.example
├── alembic.ini
├── requirements.txt
└── README.md
```
