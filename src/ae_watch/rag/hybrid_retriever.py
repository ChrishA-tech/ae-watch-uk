"""Hybrid RAG Retriever with Reciprocal Rank Fusion (RRF) and Cross-Encoder Reranking.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

from typing import Any

from ae_watch.graph.populator import ClinicalKnowledgeGraphPopulator, graph_populator
from ae_watch.rag.vector_store import OperationalVectorStore, vector_store
from ae_watch.utils.logger import logger


class HybridClinicalRetriever:
    """Fuses pgvector cosine search, PostgreSQL BM25 text search, and Neo4j subgraph traversal."""

    def __init__(
        self,
        store: OperationalVectorStore = vector_store,
        graph: ClinicalKnowledgeGraphPopulator = graph_populator,
        use_cross_encoder: bool = True,
    ):
        self.store = store
        self.graph = graph
        self.use_cross_encoder = use_cross_encoder
        self._cross_encoder = None

    def _get_cross_encoder(self):
        """Lazily initialize cross-encoder reranker with fallback."""
        if self._cross_encoder is None and self.use_cross_encoder:
            try:
                from sentence_transformers import CrossEncoder

                self._cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            except (ImportError, RuntimeError, ValueError) as exc:
                logger.warning(
                    "cross_encoder_init_failed_falling_back_to_rrf",
                    error=str(exc),
                )
                self.use_cross_encoder = False
        return self._cross_encoder

    def retrieve(
        self,
        query: str,
        trust_code: str = "REM",
        top_k: int = 3,
        dense_weight: float = 1.0,
        sparse_weight: float = 0.8,
    ) -> dict[str, Any]:
        """Execute hybrid search combining pgvector, PostgreSQL BM25, and Neo4j graph context."""
        logger.info("executing_hybrid_retrieval", query=query, trust=trust_code)

        # 1. Dense vector search
        dense_results = self.store.dense_search(query, limit=top_k * 2)

        # 2. Sparse BM25 keyword search
        sparse_results = self.store.sparse_search(query, limit=top_k * 2)

        # 3. Multi-hop Neo4j Knowledge Graph Traversal
        graph_context = self.graph.traverse_catchment_escalation(trust_code)

        # 4. Reciprocal Rank Fusion (RRF)
        # RRF score = sum(weight / (60 + rank))
        rrf_scores: dict[str, float] = {}
        doc_map: dict[str, dict[str, Any]] = {}

        for rank, doc in enumerate(dense_results):
            pid = doc["policy_id"]
            doc_map[pid] = doc
            rrf_scores[pid] = rrf_scores.get(pid, 0.0) + dense_weight / (60.0 + rank + 1)

        for rank, doc in enumerate(sparse_results):
            pid = doc["policy_id"]
            doc_map[pid] = doc
            rrf_scores[pid] = rrf_scores.get(pid, 0.0) + sparse_weight / (60.0 + rank + 1)

        # If a policy addresses an active graph intervention, boost its score
        active_interventions = set(graph_context.get("active_interventions") or [])
        for pid, doc in doc_map.items():
            category = doc.get("category", "")
            title = doc.get("title", "")
            for inv in active_interventions:
                if inv.lower() in category.lower() or inv.lower() in title.lower():
                    rrf_scores[pid] = rrf_scores.get(pid, 0.0) + 0.02

        # Sort candidate documents by RRF score
        sorted_pids = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)
        candidates = [doc_map[pid] for pid in sorted_pids[: top_k * 2]]

        # 5. Cross-Encoder Reranking
        cross_encoder = self._get_cross_encoder()
        if cross_encoder and candidates:
            try:
                pairs = [[query, f"{c['title']}: {c['chunk_text']}"] for c in candidates]
                scores = cross_encoder.predict(pairs)
                ranked_pairs = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
                final_docs = [p[0] for p in ranked_pairs[:top_k]]
            except (RuntimeError, ValueError) as exc:
                logger.warning("cross_encoder_scoring_failed_using_rrf", error=str(exc))
                final_docs = candidates[:top_k]
        else:
            final_docs = candidates[:top_k]

        return {
            "query": query,
            "trust_code": trust_code,
            "policy_chunks": final_docs,
            "graph_context": graph_context,
            "total_retrieved": len(final_docs),
        }


hybrid_retriever = HybridClinicalRetriever()
