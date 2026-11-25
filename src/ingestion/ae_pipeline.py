"""AE-Watch UK Ingestion Pipeline: Pandera Contracts, UK GDPR Pseudonymisation, DuckDB & Quarantine.

Author: CHRISH PEP FELIX A
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import pandera.pandas as pa
import structlog

from src.ingestion.live_nhs_connectors import fetch_live_nhs_and_weather_telemetry

logger = structlog.get_logger("ae_watch.v2.pipeline")

DEFAULT_DUCKDB_PATH = Path("data/processed/aewatch.duckdb")
DEFAULT_QUARANTINE_PATH = Path("data/quarantine/ae_quarantine.parquet")

# Strict Pandera Schema Contract for NHS Trust A&E SitRep Records
AETrustSitRepSchema = pa.DataFrameSchema(
    columns={
        "trust_ods_code": pa.Column(
            str,
            checks=[
                pa.Check.str_matches(r"^[A-Z0-9]{3,5}$", error="Invalid NHS ODS Trust code format"),
            ],
            nullable=False,
        ),
        "trust_name": pa.Column(str, checks=[pa.Check.str_length(min_value=3)], nullable=False),
        "type1_attendances": pa.Column(
            int,
            checks=[pa.Check.ge(0, error="Type 1 attendances must be non-negative")],
            coerce=True,
        ),
        "type2_attendances": pa.Column(
            int,
            checks=[pa.Check.ge(0, error="Type 2 attendances must be non-negative")],
            coerce=True,
        ),
        "type3_attendances": pa.Column(
            int,
            checks=[pa.Check.ge(0, error="Type 3 attendances must be non-negative")],
            coerce=True,
        ),
        "four_hour_compliance_ratio": pa.Column(
            float,
            checks=[
                pa.Check.in_range(0.0, 1.0, error="4-hour compliance ratio must lie in [0.0, 1.0]")
            ],
            coerce=True,
        ),
        "twelve_hour_trolley_waits": pa.Column(
            int, checks=[pa.Check.ge(0, error="12-hour trolley waits must be >= 0")], coerce=True
        ),
        "bed_occupancy_ratio": pa.Column(
            float,
            checks=[
                pa.Check.in_range(0.0, 1.0, error="Bed occupancy ratio must lie in [0.0, 1.0]")
            ],
            coerce=True,
        ),
        "temp_c": pa.Column(float, checks=[pa.Check.in_range(-35.0, 50.0)], coerce=True),
    },
    strict=False,
    coerce=True,
)


def pseudonymise_nhs_identifier(raw_identifier: str | None, salt: str | None = None) -> str:
    """Apply UK GDPR compliant HMAC-SHA256 pseudonymisation to NHS/incident identifiers."""
    if raw_identifier is None or str(raw_identifier).strip() == "":
        return ""
    key = (salt or os.getenv("AEWATCH_GDPR_SALT", "ae-watch-uk-gdpr-pseudonym-key-2026")).encode(
        "utf-8"
    )
    normalized = str(raw_identifier).replace(" ", "").replace("-", "").strip().encode("utf-8")
    digest = hmac.new(key, normalized, hashlib.sha256).hexdigest()
    return f"PSEUDO_{digest[:24]}"


def validate_and_quarantine_sitrep(
    df: pd.DataFrame,
    quarantine_path: Path = DEFAULT_QUARANTINE_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate rows against AETrustSitRepSchema; quarantine failing rows to Parquet."""
    quarantine_path.parent.mkdir(parents=True, exist_ok=True)
    if df.empty:
        return df.copy(), pd.DataFrame()

    try:
        valid_df = AETrustSitRepSchema.validate(df, lazy=True)
        return valid_df, pd.DataFrame()
    except pa.errors.SchemaErrors as err:
        failure_cases = err.failure_cases.copy()
        bad_indices = sorted(
            {
                int(idx)
                for idx in failure_cases["index"].dropna().tolist()
                if isinstance(idx, (int, float))
            }
        )

        # Build per-row diagnostics
        diagnostics_by_idx: dict[int, list[dict[str, Any]]] = {}
        for _, f_row in failure_cases.iterrows():
            raw_idx = f_row.get("index")
            if pd.isna(raw_idx):
                continue
            idx_int = int(raw_idx)
            diagnostics_by_idx.setdefault(idx_int, []).append(
                {
                    "column": str(f_row.get("column")),
                    "check": str(f_row.get("check")),
                    "failure_case": str(f_row.get("failure_case")),
                }
            )

        quarantine_df = df.loc[df.index.isin(bad_indices)].copy()
        quarantine_df["quarantine_reason"] = [
            json.dumps(diagnostics_by_idx.get(int(idx), [{"error": "schema_failure"}]))
            for idx in quarantine_df.index
        ]
        quarantine_df["quarantined_at"] = datetime.now(UTC).isoformat()

        # Persist dead-letter rows to Parquet (appending if already exists)
        if not quarantine_df.empty:
            if quarantine_path.exists():
                existing_q = pd.read_parquet(quarantine_path)
                combined_q = pd.concat([existing_q, quarantine_df], ignore_index=True)
            else:
                combined_q = quarantine_df
            combined_q.to_parquet(quarantine_path, index=False)
            logger.warning(
                "sitrep_rows_quarantined",
                quarantined_count=len(quarantine_df),
                quarantine_path=str(quarantine_path),
            )

        clean_input = df.drop(index=bad_indices).reset_index(drop=True)
        if clean_input.empty:
            return clean_input, quarantine_df
        valid_df = AETrustSitRepSchema.validate(clean_input, lazy=False)
        return valid_df, quarantine_df


def apply_uk_gdpr_pseudonymisation(df: pd.DataFrame) -> pd.DataFrame:
    """Pseudonymise sensitive identifiers and strip raw NHS numbers before persistence."""
    out = df.copy()
    if "patient_nhs_number" in out.columns:
        out["patient_pseudonym_id"] = out["patient_nhs_number"].apply(pseudonymise_nhs_identifier)
        out = out.drop(columns=["patient_nhs_number"])
    if "incident_id" in out.columns:
        out["incident_pseudonym_id"] = out["incident_id"].apply(pseudonymise_nhs_identifier)
        out = out.drop(columns=["incident_id"])
    return out


def persist_to_duckdb(
    df: pd.DataFrame,
    duckdb_path: Path = DEFAULT_DUCKDB_PATH,
    table_name: str = "trust_sitrep_daily",
) -> int:
    """Persist validated & GDPR-pseudonymised telemetry to DuckDB."""
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(duckdb_path)) as conn:
        conn.register("_staged_df", df)
        conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM _staged_df")
        row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    logger.info("duckdb_persisted", table=table_name, rows=row_count, path=str(duckdb_path))
    return int(row_count)


def run_ae_ingestion_pipeline(
    live: bool = True,
    raw_override_df: pd.DataFrame | None = None,
    duckdb_path: Path = DEFAULT_DUCKDB_PATH,
    quarantine_path: Path = DEFAULT_QUARANTINE_PATH,
) -> dict[str, Any]:
    """Execute end-to-end v2 ingestion: fetch -> Pandera quarantine -> GDPR -> DuckDB."""
    raw_df = (
        raw_override_df.copy()
        if raw_override_df is not None
        else fetch_live_nhs_and_weather_telemetry(live=live)
    )
    feed_status = (
        str(raw_df["feed_status"].iloc[0])
        if not raw_df.empty and "feed_status" in raw_df.columns
        else "UNKNOWN"
    )

    valid_df, quarantined_df = validate_and_quarantine_sitrep(
        raw_df, quarantine_path=quarantine_path
    )
    pseudonymised_df = apply_uk_gdpr_pseudonymisation(valid_df)
    persisted_rows = persist_to_duckdb(pseudonymised_df, duckdb_path=duckdb_path)

    return {
        "status": "success",
        "feed_status": feed_status,
        "raw_rows": len(raw_df),
        "valid_rows": len(pseudonymised_df),
        "quarantined_rows": len(quarantined_df),
        "persisted_rows": persisted_rows,
        "duckdb_path": str(duckdb_path),
        "quarantine_path": str(quarantine_path),
        "df": pseudonymised_df,
    }
