"""Resilient Embedding Generation Client using Gemini Embedding 2.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

import hashlib
import math
from collections.abc import Sequence

import numpy as np
from google import genai
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ae_watch.config import settings
from ae_watch.utils.logger import logger

EMBEDDING_DIM = 3072


class GeminiEmbeddingClient:
    """Generates 3072-dimensional embeddings via Gemini with retry and offline fallback."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_embedding_model
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _generate_fallback_embedding(self, text: str, dim: int = EMBEDDING_DIM) -> list[float]:
        """Generate deterministic pseudo-random embedding vector for offline testing."""
        # Use SHA-256 hash of text to seed a deterministic pseudo-random projection
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.RandomState(seed)
        vec = rng.randn(dim).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=False,
    )
    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string into a 3072-dim float vector."""
        if not self.api_key:
            return self._generate_fallback_embedding(text)

        try:
            client = self._get_client()
            res = client.models.embed_content(
                model=self.model,
                contents=text,
            )
            if res.embeddings and len(res.embeddings) > 0:
                values = res.embeddings[0].values
                # Normalize vector to unit length
                norm = math.sqrt(sum(x * x for x in values))
                return [x / norm for x in values] if norm > 0 else values
        except (genai.errors.APIError, RuntimeError, ValueError) as exc:
            logger.warning(
                "gemini_embedding_api_failed_falling_back_to_deterministic",
                model=self.model,
                error=str(exc),
            )

        return self._generate_fallback_embedding(text)

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed multiple text chunks sequentially or via fallback."""
        embeddings: list[list[float]] = []
        for text in texts:
            emb = self.embed_text(text)
            embeddings.append(emb)
        return embeddings


embedding_client = GeminiEmbeddingClient()
