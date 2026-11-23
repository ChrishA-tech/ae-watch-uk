"""Unit and integration tests for pgvector RAG and Hybrid Retrieval.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

from ae_watch.rag.embeddings import EMBEDDING_DIM, embedding_client
from ae_watch.rag.hybrid_retriever import hybrid_retriever
from ae_watch.rag.vector_store import vector_store


def test_embedding_client_dimension_and_normalization():
    """Verify embedding client outputs 3072-dimensional normalized vectors."""
    text = "NHS England Urgent and Emergency Care Recovery Plan"
    vec = embedding_client.embed_text(text)

    assert len(vec) == EMBEDDING_DIM
    # Check normalized unit length approx 1.0
    norm = sum(x * x for x in vec) ** 0.5
    assert 0.99 <= norm <= 1.01


def test_vector_store_ingestion_and_counts():
    """Verify pgvector schema creation and standard policy chunk ingestion."""
    count = vector_store.ingest_standards()
    assert count >= 8


def test_dense_and_sparse_search():
    """Verify both dense cosine search and BM25 sparse search return relevant results."""
    query = "4-hour standard A&E 78% target"

    # Dense vector search
    dense_res = vector_store.dense_search(query, limit=3)
    assert len(dense_res) > 0
    assert "similarity_score" in dense_res[0]

    # Sparse keyword search
    sparse_res = vector_store.sparse_search(query, limit=3)
    assert len(sparse_res) > 0
    assert "rank_score" in sparse_res[0]


def test_hybrid_retrieval_rrf_and_graph_fusion():
    """Verify hybrid RRF retrieval combines vector search with Neo4j graph context."""
    res = hybrid_retriever.retrieve(
        query="What are the escalation triggers when ambulance handovers breach 45 minutes?",
        trust_code="REM",
        top_k=3,
    )

    assert res["trust_code"] == "REM"
    assert len(res["policy_chunks"]) == 3
    assert "graph_context" in res
    assert res["graph_context"]["trust_code"] == "REM"

    # Top policy should be ambulance handover or OPEL escalation
    top_policy_ids = [p["policy_id"] for p in res["policy_chunks"]]
    assert "NHS-UEC-STD-002" in top_policy_ids or "NHS-UEC-STD-007" in top_policy_ids
