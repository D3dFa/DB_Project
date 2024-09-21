# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    Base.metadata.create_all(bind=engine)
