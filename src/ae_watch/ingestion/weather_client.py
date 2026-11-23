"""Open-Meteo Historical & Forecast Weather Ingestion Client.

Maps meteorological telemetry (temperatures, wind chill, precipitation)
to NHS Trust primary hospital site coordinates (Liverpool REM and Cheshire & Merseyside).
Author: CHRISH PEP FELIX A
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

import httpx
import psycopg

from ae_watch.config import settings
from ae_watch.ingestion.lineage import lineage_client
from ae_watch.ingestion.quarantine import quarantine_handler
from ae_watch.ingestion.schemas import OpenMeteoWeatherRecord
from ae_watch.utils.logger import logger
from ae_watch.utils.resilience import execute_with_resilience

ARCHIVE_API_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"

# Primary hospital site coordinates for target NHS Trusts
TRUST_COORDINATES = [
    {
        "trust_code": "REM",
        "hospital_name": "Royal Liverpool University Hospital",
        "latitude": 53.4093,
        "longitude": -2.9566,
    },
    {
        "trust_code": "REM",
        "hospital_name": "Aintree University Hospital",
        "latitude": 53.4684,
        "longitude": -2.9431,
    },
    {
        "trust_code": "RBL",
        "hospital_name": "Arrowe Park Hospital (Wirral)",
        "latitude": 53.3644,
        "longitude": -3.0782,
    },
    {
        "trust_code": "RWW",
        "hospital_name": "Warrington Hospital",
        "latitude": 53.3768,
        "longitude": -2.6074,
    },
    {
        "trust_code": "RJR",
        "hospital_name": "Countess of Chester Hospital",
        "latitude": 53.2104,
        "longitude": -2.8986,
    },
    {
        "trust_code": "RBS",
        "hospital_name": "Alder Hey Children's Hospital",
        "latitude": 53.4243,
        "longitude": -2.8953,
    },
    {
        "trust_code": "REP",
        "hospital_name": "Liverpool Women's Hospital",
        "latitude": 53.3965,
        "longitude": -2.9602,
    },
]


class OpenMeteoClient:
    """Async client for Open-Meteo weather telemetry."""

    def __init__(self, pg_conn_uri: str | None = None):
        self.pg_conn_uri = pg_conn_uri or settings.postgres_connection_uri

    async def fetch_weather_for_site(
        self,
        client: httpx.AsyncClient,
        site: dict[str, Any],
        start_date: str = "2024-01-01",
        end_date: str = "2026-11-20",
    ) -> list[OpenMeteoWeatherRecord]:
        """Fetch historical daily weather archive for a specific hospital site."""
        params = {
            "latitude": site["latitude"],
            "longitude": site["longitude"],
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,apparent_temperature_min,wind_speed_10m_max,precipitation_sum",
            "timezone": "Europe/London",
        }

        logger.info(
            "fetching_meteo_archive",
            trust_code=site["trust_code"],
            hospital=site["hospital_name"],
            start=start_date,
            end=end_date,
        )

        resp = await execute_with_resilience(
            client.get,
            ARCHIVE_API_URL,
            params=params,
            headers={"User-Agent": "AE-Watch-UK/0.1.0 (Research Ingestion; CHRISH PEP FELIX A)"},
            timeout=25.0,
        )
        data = resp.json()
        daily = data.get("daily", {})

        records: list[OpenMeteoWeatherRecord] = []
        times = daily.get("time", [])
        t_maxs = daily.get("temperature_2m_max", [])
        t_mins = daily.get("temperature_2m_min", [])
        t_means = daily.get("temperature_2m_mean", [])
        app_mins = daily.get("apparent_temperature_min", [])
        wind_maxs = daily.get("wind_speed_10m_max", [])
        precips = daily.get("precipitation_sum", [])

        for i, date_str in enumerate(times):
            rec_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            payload = {
                "trust_code": site["trust_code"],
                "hospital_name": site["hospital_name"],
                "latitude": site["latitude"],
                "longitude": site["longitude"],
                "record_date": rec_date,
                "temp_min_c": t_mins[i] if i < len(t_mins) else None,
                "temp_mean_c": t_means[i] if i < len(t_means) else None,
                "temp_max_c": t_maxs[i] if i < len(t_maxs) else None,
                "apparent_temp_min_c": app_mins[i] if i < len(app_mins) else None,
                "wind_speed_max_kmh": wind_maxs[i] if i < len(wind_maxs) else None,
                "precipitation_sum_mm": precips[i] if i < len(precips) else None,
                "is_forecast": False,
            }

            validated = quarantine_handler.validate_or_quarantine(
                OpenMeteoWeatherRecord,
                payload,
                source_pipeline="open_meteo_weather",
                trust_code_key="trust_code",
            )
            if validated:
                records.append(validated)

        return records

    def persist_to_bronze(self, records: Sequence[OpenMeteoWeatherRecord]) -> int:
        """Insert validated weather records into bronze.open_meteo_raw."""
        if not records:
            return 0

        inserted = 0
        with psycopg.connect(self.pg_conn_uri) as conn:
            with conn.cursor() as cur:
                for rec in records:
                    cur.execute(
                        """
                        INSERT INTO bronze.open_meteo_raw
                        (trust_code, hospital_name, latitude, longitude, record_date,
                         temp_min_c, temp_mean_c, temp_max_c, apparent_temp_min_c,
                         wind_speed_max_kmh, precipitation_sum_mm, is_forecast, ingested_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            rec.trust_code,
                            rec.hospital_name,
                            rec.latitude,
                            rec.longitude,
                            rec.record_date,
                            rec.temp_min_c,
                            rec.temp_mean_c,
                            rec.temp_max_c,
                            rec.apparent_temp_min_c,
                            rec.wind_speed_max_kmh,
                            rec.precipitation_sum_mm,
                            rec.is_forecast,
                        ),
                    )
                    inserted += 1
            conn.commit()

        logger.info("persisted_meteo_records_to_bronze", count=inserted)
        return inserted

    async def run(
        self,
        sites: list[dict[str, Any]] | None = None,
        start_date: str = "2024-01-01",
        end_date: str = "2026-11-20",
    ) -> int:
        """Execute full async weather ingestion pipeline with OpenLineage telemetry."""
        target_sites = sites or TRUST_COORDINATES
        job_name = "ae_watch.ingestion.open_meteo"
        inputs = [{"namespace": ARCHIVE_API_URL, "name": s["hospital_name"]} for s in target_sites]
        outputs = [{"namespace": settings.postgres_db, "name": "bronze.open_meteo_raw"}]

        async with lineage_client.track_run(job_name, inputs=inputs, outputs=outputs):
            total_persisted = 0
            async with httpx.AsyncClient() as client:
                for site in target_sites:
                    try:
                        records = await self.fetch_weather_for_site(
                            client, site, start_date=start_date, end_date=end_date
                        )
                        persisted = self.persist_to_bronze(records)
                        total_persisted += persisted
                    except Exception as exc:
                        logger.error(
                            "meteo_site_ingestion_error",
                            site=site["hospital_name"],
                            error=str(exc),
                        )
                        raise

            logger.info("meteo_ingestion_completed", total_records=total_persisted)
            return total_persisted


weather_client = OpenMeteoClient()
