"""PostgreSQL pgvector Knowledge Base for NHS Operational Standards.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

import json
from typing import Any

import psycopg
from pgvector.psycopg import register_vector

from ae_watch.config import settings
from ae_watch.rag.embeddings import EMBEDDING_DIM, GeminiEmbeddingClient, embedding_client
from ae_watch.rag.standards import OFFICIAL_UEC_STANDARDS
from ae_watch.utils.logger import logger


class OperationalVectorStore:
    """Manages dense pgvector embeddings and full-text keyword indexing in PostgreSQL."""

    def __init__(
        self,
        pg_conn_uri: str | None = None,
        embedder: GeminiEmbeddingClient = embedding_client,
    ):
        self.uri = pg_conn_uri or settings.postgres_connection_uri
        self.embedder = embedder

    def init_schema(self) -> None:
        """Create vector extension, rag schema, tables, and indexes."""
        logger.info("initializing_pgvector_rag_schema")

        ddl = f"""
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE SCHEMA IF NOT EXISTS rag;

        CREATE TABLE IF NOT EXISTS rag.operational_standards (
            id SERIAL PRIMARY KEY,
            policy_id VARCHAR(64) UNIQUE NOT NULL,
            title VARCHAR(255) NOT NULL,
            category VARCHAR(64) NOT NULL,
            citation VARCHAR(255) NOT NULL,
            chunk_text TEXT NOT NULL,
            mandatory_actions JSONB DEFAULT '[]'::jsonb,
            embedding vector({EMBEDDING_DIM}) NOT NULL,
            tsv_content tsvector GENERATED ALWAYS AS (
                to_tsvector('english', title || ' ' || category || ' ' || chunk_text)
            ) STORED,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_rag_standards_tsv
            ON rag.operational_standards USING gin (tsv_content);
        """

        with psycopg.connect(self.uri) as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
            conn.commit()

        logger.info("pgvector_rag_schema_initialized")

    def ingest_standards(self, standards: list[dict[str, Any]] | None = None) -> int:
        """Embed and ingest operational standards into PostgreSQL."""
        self.init_schema()
        records_to_insert = standards or OFFICIAL_UEC_STANDARDS
        logger.info("ingesting_operational_standards", count=len(records_to_insert))

        inserted = 0
        with psycopg.connect(self.uri) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                for item in records_to_insert:
                    # Generate embedding
                    full_text = f"{item['title']}. {item['chunk_text']}"
                    embedding_vector = self.embedder.embed_text(full_text)

                    cur.execute(
                        """
                        INSERT INTO rag.operational_standards (
                            policy_id, title, category, citation, chunk_text, mandatory_actions, embedding
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (policy_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            category = EXCLUDED.category,
                            citation = EXCLUDED.citation,
                            chunk_text = EXCLUDED.chunk_text,
                            mandatory_actions = EXCLUDED.mandatory_actions,
                            embedding = EXCLUDED.embedding;
                        """,
                        (
                            item["policy_id"],
                            item["title"],
                            item["category"],
                            item["citation"],
                            item["chunk_text"],
                            json.dumps(item["mandatory_actions"]),
                            embedding_vector,
                        ),
                    )
                    inserted += 1
            conn.commit()

        logger.info("operational_standards_ingested", total_inserted=inserted)
        return inserted

    def dense_search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Dense similarity search using cosine distance (<=>)."""
        query_vec = self.embedder.embed_text(query)

        query_sql = """
        SELECT
            policy_id,
            title,
            category,
            citation,
            chunk_text,
            mandatory_actions,
            1.0 - (embedding <=> %s::vector) AS similarity_score
        FROM rag.operational_standards
        ORDER BY embedding <=> %s::vector ASC
        LIMIT %s;
        """

        with psycopg.connect(self.uri) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.execute(query_sql, (query_vec, query_vec, limit))
                cols = [desc[0] for desc in cur.description]
                rows = cur.fetchall()

        return [dict(zip(cols, r)) for r in rows]

    def sparse_search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Full-text BM25 keyword search using PostgreSQL ts_rank."""
        query_sql = """
        SELECT
            policy_id,
            title,
            category,
            citation,
            chunk_text,
            mandatory_actions,
            ts_rank_cd(tsv_content, plainto_tsquery('english', %s)) AS rank_score
        FROM rag.operational_standards
        WHERE tsv_content @@ plainto_tsquery('english', %s)
        ORDER BY rank_score DESC
        LIMIT %s;
        """

        with psycopg.connect(self.uri) as conn, conn.cursor() as cur:
            cur.execute(query_sql, (query, query, limit))
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

        return [dict(zip(cols, r)) for r in rows]


vector_store = OperationalVectorStore()
