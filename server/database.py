import os
import sqlalchemy as sa
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, echo=False)


def create_db_and_tables():
    """Create all SQLModel tables on startup."""
    SQLModel.metadata.create_all(engine)
    _apply_additive_schema_updates()


def get_session():
    """FastAPI dependency that yields a database session."""
    with Session(engine) as session:
        yield session


def _apply_additive_schema_updates():
    """Apply small additive schema updates for environments without migrations."""
    inspector = sa.inspect(engine)

    if "swipe" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("swipe")}
    statements: list[str] = []
    dialect = engine.dialect.name

    if "keyword_score" not in existing_columns:
        if dialect == "postgresql":
            statements.append("ALTER TABLE swipe ADD COLUMN keyword_score DOUBLE PRECISION")
        else:
            statements.append("ALTER TABLE swipe ADD COLUMN keyword_score FLOAT")

    if "keyword_reasoning" not in existing_columns:
        statements.append("ALTER TABLE swipe ADD COLUMN keyword_reasoning TEXT")

    if "keyword_approved" not in existing_columns:
        if dialect == "postgresql":
            statements.append("ALTER TABLE swipe ADD COLUMN keyword_approved BOOLEAN")
        else:
            statements.append("ALTER TABLE swipe ADD COLUMN keyword_approved BOOLEAN")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(sa.text(statement))
