"""OpenLineage telemetry client emitting events to Marquez.

Emits standard START, COMPLETE, and FAIL lifecycle events with structured
JSON stack traces, error facets, and dataset metadata.
Author: CHRISH PEP FELIX A
"""

import traceback
import uuid
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import httpx

from ae_watch.config import settings
from ae_watch.utils.logger import logger


class OpenLineageTelemetry:
    """Sends OpenLineage v1 events to Marquez backend."""

    def __init__(
        self,
        base_url: str | None = None,
        namespace: str | None = None,
        producer: str = "https://github.com/chrish-pep-felix-a/ae-watch-uk",
    ):
        self.base_url = (base_url or settings.openlineage_url).rstrip("/")
        self.namespace = namespace or settings.openlineage_namespace
        self.producer = producer
        self.endpoint = f"{self.base_url}/api/v1/lineage"

    def build_event(
        self,
        event_type: str,
        job_name: str,
        run_id: str,
        inputs: Sequence[dict[str, Any]] | None = None,
        outputs: Sequence[dict[str, Any]] | None = None,
        error_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Construct a validated OpenLineage v1 JSON event payload."""
        now_iso = datetime.now(UTC).isoformat()
        run_facets: dict[str, Any] = {
            "nominalTime": {
                "_producer": self.producer,
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/NominalTimeRunFacet.json",
                "nominalStartTime": now_iso,
            }
        }

        if error_info:
            run_facets["errorMessage"] = {
                "_producer": self.producer,
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/ErrorMessageRunFacet.json",
                "message": error_info.get("message", "Pipeline execution failure"),
                "programmingLanguage": "python",
                "stackTrace": error_info.get("stackTrace", ""),
            }

        job_facets = {
            "documentation": {
                "_producer": self.producer,
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DocumentationJobFacet.json",
                "description": f"AE-Watch UK Pipeline: {job_name} (Author: CHRISH PEP FELIX A)",
            }
        }

        return {
            "eventType": event_type.upper(),
            "eventTime": now_iso,
            "run": {
                "runId": run_id,
                "facets": run_facets,
            },
            "job": {
                "namespace": self.namespace,
                "name": job_name,
                "facets": job_facets,
            },
            "inputs": list(inputs or []),
            "outputs": list(outputs or []),
            "producer": self.producer,
            "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json",
        }

    async def emit_event(self, event: dict[str, Any]) -> bool:
        """Transmit OpenLineage event to Marquez endpoint."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    self.endpoint,
                    json=event,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code in {200, 201}:
                    logger.debug(
                        "openlineage_event_emitted",
                        event_type=event.get("eventType"),
                        job=event.get("job", {}).get("name"),
                        run_id=event.get("run", {}).get("runId"),
                    )
                    return True
                else:
                    logger.warning(
                        "marquez_rejected_event",
                        status_code=resp.status_code,
                        response=resp.text,
                    )
                    return False
        except (httpx.HTTPError, OSError) as exc:
            # Telemetry delivery failure should be logged but never crash the core pipeline
            logger.warning(
                "marquez_telemetry_unreachable",
                endpoint=self.endpoint,
                error=str(exc),
            )
            return False

    @asynccontextmanager
    async def track_run(
        self,
        job_name: str,
        inputs: Sequence[dict[str, Any]] | None = None,
        outputs: Sequence[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Context manager tracking START, COMPLETE, and FAIL events."""
        run_id = str(uuid.uuid4())
        # 1. Emit START event
        start_event = self.build_event("START", job_name, run_id, inputs=inputs, outputs=outputs)
        await self.emit_event(start_event)

        try:
            yield run_id
            # 2. Emit COMPLETE event on clean exit
            complete_event = self.build_event(
                "COMPLETE", job_name, run_id, inputs=inputs, outputs=outputs
            )
            await self.emit_event(complete_event)
        except Exception as exc:
            # 3. Emit FAIL event with structured error stack trace
            error_info = {
                "message": f"{type(exc).__name__}: {exc!s}",
                "stackTrace": traceback.format_exc(),
            }
            fail_event = self.build_event(
                "FAIL", job_name, run_id, inputs=inputs, outputs=outputs, error_info=error_info
            )
            await self.emit_event(fail_event)
            logger.error(
                "pipeline_failed_lineage_emitted",
                job_name=job_name,
                run_id=run_id,
                error=str(exc),
            )
            raise


lineage_client = OpenLineageTelemetry()
