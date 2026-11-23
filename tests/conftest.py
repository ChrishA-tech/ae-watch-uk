"""Pytest shared fixtures and configuration for AE-Watch UK.

Author: CHRISH PEP FELIX A
"""

import os

import psycopg
import pytest

from ae_watch.config import settings

# Ensure test runs target local environment
os.environ["OPENLINEAGE_NAMESPACE"] = "ae-watch-uk-test"


@pytest.fixture(scope="session")
def db_conn():
    """Session-scoped database connection to verify Postgres tables."""
    conn = psycopg.connect(settings.postgres_connection_uri)
    yield conn
    conn.close()


@pytest.fixture
def clean_quarantine_table(db_conn):
    """Clean quarantine errors before and after specific quarantine tests."""
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM quarantine.ingestion_errors WHERE source_pipeline LIKE 'test_%';")
    db_conn.commit()
    yield
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM quarantine.ingestion_errors WHERE source_pipeline LIKE 'test_%';")
    db_conn.commit()
