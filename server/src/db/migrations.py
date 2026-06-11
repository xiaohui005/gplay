from src.db.database import Base, engine
from src.models import *


def run_migrations():
    Base.metadata.create_all(bind=engine)
