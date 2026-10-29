"""Explicit PostgreSQL configuration; migrations are a separate admin action."""
import os
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


def engine_for(url=None):
    url = url or os.environ.get("JUNO_DATABASE_URL")
    if not url or make_url(url).drivername != "postgresql+psycopg":
        raise RuntimeError("Set JUNO_DATABASE_URL to a postgresql+psycopg URL.")
    return create_engine(url, pool_pre_ping=True, hide_parameters=True)


def sessions(engine):
    return sessionmaker(engine, expire_on_commit=False)
