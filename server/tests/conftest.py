import os
import sys
import pytest

os.environ["DATABASE_URL"] = "sqlite:///./data/test_collection.db"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.database import Base, engine, SessionLocal
from src.models import *


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
