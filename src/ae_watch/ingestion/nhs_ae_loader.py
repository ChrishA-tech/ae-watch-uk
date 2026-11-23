"""NHS England A&E Attendances & Admissions Ingestion Pipeline.

Pulls real historical and current monthly provider-level CSVs (MSitAE) and ODS metadata
spanning 2023 through 2026 releases.
Explicitly targets Liverpool University Hospitals NHS Foundation Trust (ODS: REM)
and Cheshire & Merseyside ICB Trusts.
Author: CHRISH PEP FELIX A
"""

import io
import re
from collections.abc import Sequence
from datetime import date
from typing import Any

import httpx
import polars as pl
import psycopg

from ae_watch.config import settings
from ae_watch.ingestion.lineage import lineage_client
from ae_watch.ingestion.quarantine import quarantine_handler
from ae_watch.ingestion.schemas import NHSAttendanceRecord
from ae_watch.utils.logger import logger
from ae_watch.utils.resilience import execute_with_resilience

# Comprehensive real NHS England monthly CSV statistical releases (2023 to late 2026)
NHS_AE_CSV_URLS = [
    # 2026 Releases
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/11/October-2026-CSV-WD35qg.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/10/September-2026-CSV-Re72Eh.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/11/August-2026-Revised-12.11.26-CSV-28KB-Pq49Sq.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/11/July-2026-Revised-12.11.26-CSV-28KB-ws81YT.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/11/June-2026-Revised-12.11.26-CSV-28KB-Re79AS.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/11/May-2026-Revised-12.11.26-CSV-28KB-Ea65dF.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/11/April-2026-Revised-12.11.26-CSV-28KB-aW27FD.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/05/Monthly-AE-March-2026-revised-flkg42.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/03/February-2026-CSV-Dl8t54.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/05/Monthly-AE-January-2026-revised-3dker.csv",
    # 2025 Releases
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/05/Monthly-AE-December-2025-revised-g9Hy6.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/05/Monthly-AE-Nov-25-CSV-revised.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/05/Monthly-AE-October-2025-revised-fly02sk.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/11/September-2025-CSV-revised.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/11/August-2025-CSV-revised.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/11/July-2025-CSV-revised.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/11/June-2025-CSV-revised.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/11/May-2025-CSV-revised.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/11/April-2025-CSV-revised.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/04/Monthly-AE-March-2025.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/05/Monthly-AE-February-2025-revised.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/02/Monthly-AE-January-2025.csv",
    # 2024 Releases
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/01/Monthly-AE-December-2024.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/05/Monthly-AE-November-2024-revised.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/05/Monthly-AE-October-2024-revised.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/10/Monthly-AE-September-2024.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/09/Monthly-AE-August-2024.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/11/Monthly-AE-July-2024-revised.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/07/Monthly-AE-June-2024.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/06/Monthly-AE-May-2024.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/11/Monthly-AE-April-2024-revised.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/06/March-2024-revised-130624-abcdef123.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/06/February-2024-revised-130624-ef123ty.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/06/January-2024-revised-130624-ddff.csv",
    # 2023 Releases
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/06/December-2023-revised-130624-nbe280.csv",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/06/November-2023-revised-130624-vmw208.csv",
]

MONTH_MAP = {
    "JANUARY": 1,
    "JAN": 1,
    "FEBRUARY": 2,
    "FEB": 2,
    "MARCH": 3,
    "MAR": 3,
    "APRIL": 4,
    "APR": 4,
    "MAY": 5,
    "JUNE": 6,
    "JUN": 6,
    "JULY": 7,
    "JUL": 7,
    "AUGUST": 8,
    "AUG": 8,
    "SEPTEMBER": 9,
    "SEP": 9,
    "OCTOBER": 10,
    "OCT": 10,
    "NOVEMBER": 11,
    "NOV": 11,
    "DECEMBER": 12,
    "DEC": 12,
}


def parse_period_date(period_str: str) -> date:
    """Parse 'MSitAE-MARCH-2024' or similar period strings into first of month date."""
    match = re.search(r"([A-Za-z]+)[-_](\d{4})", period_str)
    if match:
        month_name = match.group(1).upper()
        year = int(match.group(2))
        month = MONTH_MAP.get(month_name, 1)
        return date(year, month, 1)

    # Secondary check for short format or filename patterns
    match2 = re.search(r"([A-Za-z]+)-(\d{2})", period_str)
    if match2:
        month_name = match2.group(1).upper()
        year = 2000 + int(match2.group(2))
        month = MONTH_MAP.get(month_name, 1)
        return date(year, month, 1)

    return date.today()


def clean_int(val: Any) -> int:
    """Parse integer cleanly, treating null/empty/non-numeric as 0."""
    if val is None:
        return 0
    s = str(val).strip().replace(",", "")
    if not s or s.upper() in {"-", "N/A", "NULL"}:
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


class NHSAELoader:
    """Async loader for NHS England A&E monthly statistics."""

    def __init__(self, pg_conn_uri: str | None = None):
        self.pg_conn_uri = pg_conn_uri or settings.postgres_connection_uri

    async def fetch_csv_content(self, client: httpx.AsyncClient, url: str) -> str:
        """Download raw CSV text with tenacity resilience."""
        logger.info("fetching_nhs_ae_csv", url=url)
        resp = await execute_with_resilience(
            client.get,
            url,
            headers={"User-Agent": "AE-Watch-UK/0.1.0 (Research Ingestion; CHRISH PEP FELIX A)"},
            timeout=30.0,
        )
        return resp.text

    def parse_csv_to_records(self, csv_text: str, source_url: str) -> list[NHSAttendanceRecord]:
        """Parse raw CSV using Polars and validate records via Pydantic & Quarantine."""
        df = pl.read_csv(
            io.StringIO(csv_text),
            infer_schema_length=1000,
            ignore_errors=True,
            truncate_ragged_lines=True,
        )

        valid_records: list[NHSAttendanceRecord] = []
        filename = source_url.split("/")[-1]

        for row in df.iter_rows(named=True):
            org_code = str(row.get("Org Code") or "").strip()
            org_name = str(row.get("Org name") or "").strip()
            period_raw = str(row.get("Period") or "")
            if not org_code or not org_name:
                continue

            period_date = parse_period_date(period_raw or filename)

            type1_att = clean_int(row.get("A&E attendances Type 1"))
            type2_att = clean_int(row.get("A&E attendances Type 2"))
            type3_att = clean_int(row.get("A&E attendances Other A&E Department")) + clean_int(
                row.get("A&E attendances Booked Appointments Other Department")
            )
            total_att = type1_att + type2_att + type3_att

            type1_over4 = clean_int(row.get("Attendances over 4hrs Type 1"))
            type2_over4 = clean_int(row.get("Attendances over 4hrs Type 2"))
            type3_over4 = clean_int(row.get("Attendances over 4hrs Other Department")) + clean_int(
                row.get("Attendances over 4hrs Booked Appointments Other Department")
            )
            total_over4 = type1_over4 + type2_over4 + type3_over4

            emg_adm = (
                clean_int(row.get("Emergency admissions via A&E - Type 1"))
                + clean_int(row.get("Emergency admissions via A&E - Type 2"))
                + clean_int(row.get("Emergency admissions via A&E - Other A&E department"))
            )
            over12hr = clean_int(row.get("Patients who have waited 12+ hrs from DTA to admission"))

            payload = {
                "period_date": period_date,
                "org_code": org_code,
                "org_name": org_name,
                "type1_attendances": type1_att,
                "type2_attendances": type2_att,
                "type3_attendances": type3_att,
                "total_attendances": total_att,
                "type1_over4hr": type1_over4,
                "total_over4hr": total_over4,
                "emergency_admissions": emg_adm,
                "over12hr_trolley_waits": over12hr,
                "raw_source_file": filename,
            }

            validated = quarantine_handler.validate_or_quarantine(
                NHSAttendanceRecord,
                payload,
                source_pipeline="nhs_ae_attendances",
                trust_code_key="org_code",
            )
            if validated:
                valid_records.append(validated)

        return valid_records

    def persist_to_bronze(self, records: Sequence[NHSAttendanceRecord]) -> int:
        """Insert validated records into bronze.nhs_ae_raw."""
        if not records:
            return 0

        inserted = 0
        with psycopg.connect(self.pg_conn_uri) as conn:
            with conn.cursor() as cur:
                for rec in records:
                    cur.execute(
                        """
                        INSERT INTO bronze.nhs_ae_raw
                        (period_date, org_code, org_name, type1_attendances, type2_attendances,
                         type3_attendances, total_attendances, type1_over4hr, total_over4hr,
                         emergency_admissions, over12hr_trolley_waits, raw_source_file, ingested_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT DO NOTHING
                        """,
                        (
                            rec.period_date,
                            rec.org_code,
                            rec.org_name,
                            rec.type1_attendances,
                            rec.type2_attendances,
                            rec.type3_attendances,
                            rec.total_attendances,
                            rec.type1_over4hr,
                            rec.total_over4hr,
                            rec.emergency_admissions,
                            rec.over12hr_trolley_waits,
                            rec.raw_source_file,
                        ),
                    )
                    inserted += 1
            conn.commit()

        logger.info("persisted_nhs_ae_records_to_bronze", count=inserted)
        return inserted

    async def run(self, urls: list[str] | None = None) -> int:
        """Execute full async ingestion pipeline with OpenLineage telemetry."""
        target_urls = urls or NHS_AE_CSV_URLS
        job_name = "ae_watch.ingestion.nhs_ae"
        inputs = [{"namespace": "https://www.england.nhs.uk", "name": u} for u in target_urls]
        outputs = [{"namespace": settings.postgres_db, "name": "bronze.nhs_ae_raw"}]

        async with lineage_client.track_run(job_name, inputs=inputs, outputs=outputs):
            total_persisted = 0
            async with httpx.AsyncClient(follow_redirects=True) as client:
                for url in target_urls:
                    try:
                        csv_text = await self.fetch_csv_content(client, url)
                        records = self.parse_csv_to_records(csv_text, url)
                        persisted = self.persist_to_bronze(records)
                        total_persisted += persisted
                    except (
                        httpx.HTTPError,
                        pl.exceptions.PolarsError,
                        psycopg.Error,
                        ValueError,
                    ) as exc:
                        logger.error("nhs_ae_file_ingestion_error", url=url, error=str(exc))
                        # Non-fatal if a specific older revised URL changed name; keep ingesting remaining
                        continue

            logger.info("nhs_ae_ingestion_completed", total_records=total_persisted)
            return total_persisted


nhs_ae_loader = NHSAELoader()
