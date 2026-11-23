"""Configuration and environment validation tests.

Author: CHRISH PEP FELIX A
"""

from ae_watch.config import settings


def test_author_attribution():
    """Verify that author attribution is strictly CHRISH PEP FELIX A."""
    assert settings.author == "CHRISH PEP FELIX A"
    assert settings.project_name == "ae-watch-uk"


def test_free_tier_gemini_models():
    """Verify free-tier Gemini models are configured."""
    assert settings.gemini_reasoning_model == "gemini-3.8-flash"
    assert settings.gemini_fast_model == "gemini-3.5-flash-lite"
    assert settings.gemini_embedding_model == "gemini-embedding-2"
    assert bool(settings.gemini_api_key) is True


def test_benchmark_trust_target():
    """Verify primary benchmark trust is Liverpool University Hospitals (REM)."""
    assert settings.benchmark_trust_ods == "REM"
    assert "Liverpool" in settings.benchmark_trust_name
    assert "REM" in settings.cheshire_merseyside_trust_ods
    assert "RJR" in settings.cheshire_merseyside_trust_ods
    assert "RBL" in settings.cheshire_merseyside_trust_ods
