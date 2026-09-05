"""
Phase 2 database tests.
Verifies PostgreSQL connectivity, model creation, relationships, and CRUD.
"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base, get_db
from app.models.user import User
from app.models.product import Product
from app.models.inspection import Inspection
from app.models.declaration import Declaration
from app.models.rule import Rule
from app.models.violation import Violation
from app.models.evidence import Evidence
from app.models.report import Report


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def engine():
    return create_engine(settings.DATABASE_URL)


@pytest.fixture(scope="module")
def session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


# ---------------------------------------------------------------------------
# 1. Database connection
# ---------------------------------------------------------------------------
def test_database_connection(engine):
    """Verify that SQLAlchemy can connect to PostgreSQL."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


# ---------------------------------------------------------------------------
# 2. All expected tables exist
# ---------------------------------------------------------------------------
def test_tables_exist(engine):
    from sqlalchemy import inspect as sa_inspect

    inspector = sa_inspect(engine)
    tables = set(inspector.get_table_names())
    expected = {
        "users", "products", "inspections", "declarations",
        "rules", "violations", "evidence", "reports", "visual_analyses",
    }
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"


# ---------------------------------------------------------------------------
# 3. Product CRUD
# ---------------------------------------------------------------------------
def test_product_create_and_retrieve(session):
    """Create a Product, flush to DB, query it back, then rollback."""
    product = Product(name="Test Biscuits", category="food", brand="TestBrand")
    session.add(product)
    session.flush()

    retrieved = session.query(Product).filter_by(id=product.id).first()
    assert retrieved is not None
    assert retrieved.name == "Test Biscuits"
    assert retrieved.category == "food"
    assert retrieved.brand == "TestBrand"
    assert retrieved.id is not None

    session.rollback()


# ---------------------------------------------------------------------------
# 4. Foreign-key relationship: User → Inspection → Product
# ---------------------------------------------------------------------------
def test_inspection_relationships(session):
    """Verify that Inspection correctly links User and Product."""
    user = User(username="test_officer", email="test@example.com", hashed_password="x")
    product = Product(name="Test Shampoo", category="cosmetics")
    session.add_all([user, product])
    session.flush()

    inspection = Inspection(
        product_id=product.id,
        inspector_id=user.id,
        status="PENDING",
    )
    session.add(inspection)
    session.flush()

    assert inspection.product.name == "Test Shampoo"
    assert inspection.inspector.username == "test_officer"
    assert inspection in user.inspections
    assert inspection in product.inspections

    session.rollback()


# ---------------------------------------------------------------------------
# 5. Violation → Rule relationship
# ---------------------------------------------------------------------------
def test_violation_rule_relationship(session):
    user = User(username="officer2", email="officer2@example.com", hashed_password="x")
    product = Product(name="Test Soap", category="cosmetics")
    session.add_all([user, product])
    session.flush()

    inspection = Inspection(product_id=product.id, inspector_id=user.id, status="PENDING")
    rule = Rule(rule_code="MRP-TEST", title="Test MRP Rule", category="mrp")
    session.add_all([inspection, rule])
    session.flush()

    violation = Violation(
        inspection_id=inspection.id,
        rule_id=rule.id,
        field_name="mrp",
        status="FAIL",
        severity="HIGH",
    )
    session.add(violation)
    session.flush()

    assert violation.rule.rule_code == "MRP-TEST"
    assert violation in inspection.violations

    session.rollback()


# ---------------------------------------------------------------------------
# 6. get_db dependency yields a usable session
# ---------------------------------------------------------------------------
def test_get_db_dependency():
    """Ensure the FastAPI dependency yields and closes a session."""
    gen = get_db()
    db = next(gen)
    assert db is not None
    result = db.execute(text("SELECT 1"))
    assert result.scalar() == 1
    # Cleanup
    try:
        next(gen)
    except StopIteration:
        pass
