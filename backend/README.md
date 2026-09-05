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
| GET  | `/api/v1/inspections/{id}/visual-analysis` | Retrieve visual analysis results    |

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
