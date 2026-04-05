import os
import sqlalchemy as sa
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, echo=False)


def create_db_and_tables():
    """Create all SQLModel tables on startup and apply safe additive updates."""
    SQLModel.metadata.create_all(engine)
    _apply_additive_schema_updates()


def get_session():
    """FastAPI dependency that yields a database session."""
    with Session(engine) as session:
        yield session


def _apply_additive_schema_updates():
    """Apply small additive column updates for environments without migrations.

    This is intentionally limited to safe, additive column creation. Structural
    changes like unique constraints still belong in explicit SQL migrations.
    """
    inspector = sa.inspect(engine)
    table_names = set(inspector.get_table_names())
    statements: list[str] = []
    dialect = engine.dialect.name

    if "role" in table_names:
        role_columns = {column["name"] for column in inspector.get_columns("role")}
        if "max_swipes_per_day" not in role_columns:
            statements.append(
                'ALTER TABLE "role" ADD COLUMN max_swipes_per_day INTEGER NOT NULL DEFAULT 20'
            )

    if "swipe" in table_names:
        swipe_columns = {column["name"] for column in inspector.get_columns("swipe")}

        if "keyword_score" not in swipe_columns:
            if dialect == "postgresql":
                statements.append('ALTER TABLE "swipe" ADD COLUMN keyword_score DOUBLE PRECISION')
            else:
                statements.append('ALTER TABLE "swipe" ADD COLUMN keyword_score FLOAT')

        if "keyword_reasoning" not in swipe_columns:
            statements.append('ALTER TABLE "swipe" ADD COLUMN keyword_reasoning TEXT')

        if "keyword_approved" not in swipe_columns:
            statements.append('ALTER TABLE "swipe" ADD COLUMN keyword_approved BOOLEAN')

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(sa.text(statement))
