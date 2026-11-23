"""UKHSA Data Dashboard REST API Client.

Pulls weekly laboratory reports, hospital admissions, and syndromic calls for
Influenza, RSV, Norovirus, COVID-19, and NHS 111 acute respiratory indicators.
Author: CHRISH PEP FELIX A
"""

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

import httpx
import psycopg

from ae_watch.config import settings
from ae_watch.ingestion.lineage import lineage_client
from ae_watch.ingestion.quarantine import quarantine_handler
from ae_watch.ingestion.schemas import UKHSAPathogenRecord
from ae_watch.utils.logger import logger
from ae_watch.utils.resilience import execute_with_resilience

BASE_URL = "https://api.ukhsa-dashboard.data.gov.uk"

# Target surveillance metrics: National (England) and Regional (North West) spanning 2024–2026
TARGET_METRIC_PATHS = [
    # Influenza
    "/themes/infectious_disease/sub_themes/respiratory/topics/Influenza/geography_types/Nation/geographies/England/metrics/influenza_healthcare_hospitalAdmissionRateByWeek",
    "/themes/infectious_disease/sub_themes/respiratory/topics/Influenza/geography_types/Nation/geographies/England/metrics/influenza_testing_positivityByWeek",
    "/themes/infectious_disease/sub_themes/respiratory/topics/Influenza/geography_types/UKHSA Region/geographies/North West/metrics/influenza_healthcare_hospitalAdmissionRateByWeek",
    "/themes/infectious_disease/sub_themes/respiratory/topics/Influenza/geography_types/UKHSA Region/geographies/North West/metrics/influenza_testing_positivityByWeek",
    # RSV
    "/themes/infectious_disease/sub_themes/respiratory/topics/RSV/geography_types/Nation/geographies/England/metrics/rsv_healthcare_hospitalAdmissionRateByWeek",
    "/themes/infectious_disease/sub_themes/respiratory/topics/RSV/geography_types/Nation/geographies/England/metrics/rsv_testing_positivityByWeek",
    # Norovirus
    "/themes/infectious_disease/sub_themes/gastrointestinal/topics/norovirus/geography_types/Nation/geographies/England/metrics/norovirus_cases_count",
    # COVID-19 PCR Positivity & Healthcare Burden
    "/themes/infectious_disease/sub_themes/respiratory/topics/COVID-19/geography_types/Nation/geographies/England/metrics/COVID-19_testing_positivity7DayRolling",
    "/themes/infectious_disease/sub_themes/respiratory/topics/COVID-19/geography_types/Nation/geographies/England/metrics/COVID-19_healthcare_admissionRollingMean",
    # NHS 111 Acute Respiratory Syndromic Triage Calls
    "/themes/infectious_disease/sub_themes/respiratory/topics/acute-respiratory-infection/geography_types/Nation/geographies/England/metrics/acute-respiratory-infection_syndromic_NHS111triagedcalls_averageRolling7Day",
]


class UKHSAClient:
    """Async client for UKHSA Data Dashboard API."""

    def __init__(self, pg_conn_uri: str | None = None):
        self.pg_conn_uri = pg_conn_uri or settings.postgres_connection_uri

    async def fetch_metric_records(
        self,
        client: httpx.AsyncClient,
        path: str,
        page_size: int = 100,
        max_pages: int = 25,
    ) -> list[UKHSAPathogenRecord]:
        """Fetch paginated records from UKHSA API with tenacity resilience."""
        records: list[UKHSAPathogenRecord] = []
        next_url = f"{BASE_URL}{path}?page_size={page_size}"
        page = 0

        while next_url and page < max_pages:
            page += 1
            logger.info("fetching_ukhsa_page", path=path, page=page)
            resp = await execute_with_resilience(
                client.get,
                next_url,
                headers={
                    "User-Agent": "AE-Watch-UK/0.1.0 (Research Ingestion; CHRISH PEP FELIX A)"
                },
                timeout=25.0,
            )
            data = resp.json()
            results = data.get("results", [])

            for item in results:
                raw_date_str = item.get("date")
                if not raw_date_str:
                    continue
                try:
                    p_start = datetime.strptime(raw_date_str, "%Y-%m-%d").date()
                    # Daily or weekly reporting window
                    p_end = p_start + timedelta(days=6)
                except ValueError:
                    continue

                raw_val = item.get("metric_value", 0.0)
                try:
                    val = float(raw_val) if raw_val is not None else 0.0
                except (ValueError, TypeError):
                    val = 0.0

                payload: dict[str, Any] = {
                    "theme": item.get("theme", "infectious_disease"),
                    "sub_theme": item.get("sub_theme", "respiratory"),
                    "topic": item.get("topic", "Influenza"),
                    "metric": item.get("metric", "unknown"),
                    "geography_type": item.get("geography_type", "Nation"),
                    "geography_name": item.get("geography", "England"),
                    "geography_code": item.get("geography_code"),
                    "metric_value": max(0.0, val),
                    "period_start": p_start,
                    "period_end": p_end,
                }

                validated = quarantine_handler.validate_or_quarantine(
                    UKHSAPathogenRecord,
                    payload,
                    source_pipeline="ukhsa_surveillance",
                    trust_code_key="geography_code",
                )
                if validated:
                    records.append(validated)

            next_url = data.get("next")

        return records

    def persist_to_bronze(self, records: Sequence[UKHSAPathogenRecord]) -> int:
        """Insert validated UKHSA records into bronze.ukhsa_pathogens_raw."""
        if not records:
            return 0

        inserted = 0
        with psycopg.connect(self.pg_conn_uri) as conn, conn.cursor() as cur:
            for rec in records:
                cur.execute(
                    """
                    INSERT INTO bronze.ukhsa_pathogens_raw
                    (theme, sub_theme, topic, metric, geography_type, geography_name,
                     geography_code, metric_value, period_start, period_end, ingested_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        rec.theme,
                        rec.sub_theme,
                        rec.topic,
                        rec.metric,
                        rec.geography_type,
                        rec.geography_name,
                        rec.geography_code,
                        rec.metric_value,
                        rec.period_start,
                        rec.period_end,
                    ),
                )
                inserted += 1
            conn.commit()

        logger.info("persisted_ukhsa_records_to_bronze", count=inserted)
        return inserted

    async def run(self, paths: list[str] | None = None) -> int:
        """Execute full async UKHSA surveillance pipeline with OpenLineage telemetry."""
        target_paths = paths or TARGET_METRIC_PATHS
        job_name = "ae_watch.ingestion.ukhsa_pathogens"
        inputs = [{"namespace": BASE_URL, "name": p} for p in target_paths]
        outputs = [{"namespace": settings.postgres_db, "name": "bronze.ukhsa_pathogens_raw"}]

        async with lineage_client.track_run(job_name, inputs=inputs, outputs=outputs):
            total_persisted = 0
            async with httpx.AsyncClient() as client:
                for path in target_paths:
                    try:
                        records = await self.fetch_metric_records(client, path)
                        persisted = self.persist_to_bronze(records)
                        total_persisted += persisted
                    except Exception as exc:
                        logger.error("ukhsa_path_ingestion_error", path=path, error=str(exc))
                        raise

            logger.info("ukhsa_ingestion_completed", total_records=total_persisted)
            return total_persisted


ukhsa_client = UKHSAClient()
