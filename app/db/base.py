from sqlmodel import SQLModel, create_engine

DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(DATABASE_URL, echo=False)


def init_db() -> None:
    """Create tables for initial skeleton."""
    SQLModel.metadata.create_all(engine)
