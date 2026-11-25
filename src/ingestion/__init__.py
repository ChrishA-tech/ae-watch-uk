"""Ingestion Package for AE-Watch UK (v2 Live Connectors & Pandera Pipeline).

Author: CHRISH PEP FELIX A
"""

from src.ingestion.ae_pipeline import (
    AETrustSitRepSchema,
    pseudonymise_nhs_identifier,
    run_ae_ingestion_pipeline,
)
from src.ingestion.live_nhs_connectors import (
    NHS_ACUTE_TRUST_HUBS,
    fetch_live_nhs_and_weather_telemetry,
)

__all__ = [
    "NHS_ACUTE_TRUST_HUBS",
    "AETrustSitRepSchema",
    "fetch_live_nhs_and_weather_telemetry",
    "pseudonymise_nhs_identifier",
    "run_ae_ingestion_pipeline",
]
