"""RAG module for pgvector Knowledge Base and Hybrid Retrieval."""

from ae_watch.rag.embeddings import GeminiEmbeddingClient, embedding_client
from ae_watch.rag.hybrid_retriever import HybridClinicalRetriever, hybrid_retriever
from ae_watch.rag.standards import OFFICIAL_UEC_STANDARDS
from ae_watch.rag.vector_store import OperationalVectorStore, vector_store

__all__ = [
    "OFFICIAL_UEC_STANDARDS",
    "GeminiEmbeddingClient",
    "HybridClinicalRetriever",
    "OperationalVectorStore",
    "embedding_client",
    "hybrid_retriever",
    "vector_store",
]
