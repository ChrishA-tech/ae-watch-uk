"""Dead-letter quarantine handler for malformed ingestion records.

Captures Pydantic validation failures with full column-level diagnostics,
persisting them to both PostgreSQL quarantine.ingestion_errors and local JSONL.
Author: CHRISH PEP FELIX A
"""

import json
from datetime import UTC, datetime
from typing import Any, TypeVar

import psycopg
from pydantic import BaseModel, ValidationError

from ae_watch.config import settings
from ae_watch.ingestion.schemas import ColumnErrorDiagnostic
from ae_watch.utils.logger import logger

T = TypeVar("T", bound=BaseModel)


class QuarantineHandler:
    """Manages routing of corrupted/invalid rows to dead-letter quarantine."""

    def __init__(self, pg_conn_uri: str | None = None):
        self.pg_conn_uri = pg_conn_uri or settings.postgres_connection_uri
        self.quarantine_dir = settings.quarantine_dir
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    def extract_diagnostics(self, exc: ValidationError) -> list[dict[str, Any]]:
        """Extract structured column-level error diagnostics from Pydantic ValidationError."""
        diagnostics = []
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            diagnostic = ColumnErrorDiagnostic(
                field_name=loc or "root",
                error_type=err.get("type", "validation_error"),
                error_message=err.get("msg", "Unknown validation error"),
                input_value=err.get("input"),
            )
            diagnostics.append(diagnostic.model_dump())
        return diagnostics

    def write_quarantine(
        self,
        source_pipeline: str,
        trust_code: str | None,
        raw_payload: dict[str, Any],
        diagnostics: list[dict[str, Any]],
    ) -> None:
        """Persist quarantined record to PostgreSQL and backup file."""
        now_str = datetime.now(UTC).isoformat()
        quarantine_entry = {
            "source_pipeline": source_pipeline,
            "trust_code": trust_code,
            "raw_payload": raw_payload,
            "error_diagnostics": diagnostics,
            "ingested_at": now_str,
        }

        # 1. Local backup JSONL
        date_stamp = datetime.now(UTC).strftime("%Y%m%d")
        log_file = self.quarantine_dir / f"{source_pipeline}_quarantine_{date_stamp}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(quarantine_entry, default=str) + "\n")

        # 2. PostgreSQL quarantine table
        try:
            with psycopg.connect(self.pg_conn_uri) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO quarantine.ingestion_errors
                        (source_pipeline, trust_code, raw_payload, error_diagnostics, ingested_at)
                        VALUES (%s, %s, %s, %s, NOW())
                        """,
                        (
                            source_pipeline,
                            trust_code,
                            json.dumps(raw_payload, default=str),
                            json.dumps(diagnostics, default=str),
                        ),
                    )
                conn.commit()
        except (psycopg.Error, OSError) as db_exc:
            # If DB is temporarily unavailable, the local JSONL guarantees zero data loss
            logger.error(
                "quarantine_db_insert_failed",
                error=str(db_exc),
                pipeline=source_pipeline,
                trust_code=trust_code,
            )

        logger.warning(
            "record_routed_to_quarantine",
            source_pipeline=source_pipeline,
            trust_code=trust_code,
            diagnostic_count=len(diagnostics),
            diagnostics=diagnostics,
        )

    def validate_or_quarantine(
        self,
        model_cls: type[T],
        payload: dict[str, Any],
        source_pipeline: str,
        trust_code_key: str = "org_code",
    ) -> T | None:
        """Validate payload against Pydantic schema, routing to quarantine on failure."""
        try:
            return model_cls.model_validate(payload)
        except ValidationError as exc:
            diagnostics = self.extract_diagnostics(exc)
            trust_code = payload.get(trust_code_key) or payload.get("trust_code")
            self.write_quarantine(
                source_pipeline=source_pipeline,
                trust_code=str(trust_code) if trust_code else None,
                raw_payload=payload,
                diagnostics=diagnostics,
            )
            return None


quarantine_handler = QuarantineHandler()
