"""OpenLineage and Marquez Telemetry Tests.

Validates that OpenLineage START, COMPLETE, and FAIL events are formatted to spec
and emitted to Marquez with structured JSON stack traces on pipeline failures.
Author: CHRISH PEP FELIX A
"""

import httpx
import pytest
import respx

from ae_watch.ingestion.lineage import OpenLineageTelemetry


def test_build_start_event():
    """Verify START event schema compliance."""
    telemetry = OpenLineageTelemetry(base_url="http://mock-marquez:5000", namespace="test-ns")
    event = telemetry.build_event(
        event_type="START",
        job_name="test.job",
        run_id="test-run-123",
        inputs=[{"namespace": "test", "name": "input_table"}],
        outputs=[{"namespace": "test", "name": "output_table"}],
    )
    assert event["eventType"] == "START"
    assert event["job"]["name"] == "test.job"
    assert event["job"]["namespace"] == "test-ns"
    assert event["run"]["runId"] == "test-run-123"
    assert "nominalTime" in event["run"]["facets"]
    assert "errorMessage" not in event["run"]["facets"]


def test_build_fail_event_contains_stack_trace():
    """Verify FAIL event contains structured errorMessage facet with stackTrace."""
    telemetry = OpenLineageTelemetry(base_url="http://mock-marquez:5000", namespace="test-ns")
    error_info = {
        "message": "ValueError: Corrupted NHS file header",
        "stackTrace": "Traceback (most recent call last):\n  File 'test.py', line 10\nValueError: Corrupted NHS file header",
    }
    event = telemetry.build_event(
        event_type="FAIL",
        job_name="test.failing_job",
        run_id="fail-run-456",
        error_info=error_info,
    )
    assert event["eventType"] == "FAIL"
    error_facet = event["run"]["facets"]["errorMessage"]
    assert error_facet["message"] == "ValueError: Corrupted NHS file header"
    assert "Traceback" in error_facet["stackTrace"]
    assert error_facet["programmingLanguage"] == "python"


@pytest.mark.asyncio
async def test_emit_event_success():
    """Verify event is successfully transmitted to Marquez."""
    telemetry = OpenLineageTelemetry(base_url="http://mock-marquez:5000", namespace="test-ns")
    event = telemetry.build_event("COMPLETE", "test.job", "run-789")

    with respx.mock(assert_all_called=True) as router:
        router.post("http://mock-marquez:5000/api/v1/lineage").respond(201)
        success = await telemetry.emit_event(event)
        assert success is True


@pytest.mark.asyncio
async def test_emit_event_unreachable_does_not_crash():
    """Verify Marquez network failure returns False and does not crash caller."""
    telemetry = OpenLineageTelemetry(base_url="http://non-existent-host:9999", namespace="test-ns")
    event = telemetry.build_event("COMPLETE", "test.job", "run-999")

    with respx.mock(assert_all_called=True) as router:
        router.post(
            "http://non-existent-host:9999/api/v1/lineage"
        ).side_effect = httpx.ConnectError("Connection refused")
        success = await telemetry.emit_event(event)
        assert success is False


@pytest.mark.asyncio
async def test_track_run_emits_fail_on_pipeline_exception():
    """Verify track_run emits START, then FAIL with stack trace when an exception is raised."""
    telemetry = OpenLineageTelemetry(base_url="http://mock-marquez:5000", namespace="test-ns")
    emitted_events = []

    with respx.mock(assert_all_called=True) as router:

        def side_effect(request):
            import json

            emitted_events.append(json.loads(request.content))
            return httpx.Response(201)

        router.post("http://mock-marquez:5000/api/v1/lineage").mock(side_effect=side_effect)

        with pytest.raises(RuntimeError) as exc_info:
            async with telemetry.track_run("test.crashing_pipeline"):
                raise RuntimeError("Simulated unrecoverable pipeline failure")

        assert "Simulated unrecoverable pipeline failure" in str(exc_info.value)
        assert len(emitted_events) == 2
        assert emitted_events[0]["eventType"] == "START"
        assert emitted_events[1]["eventType"] == "FAIL"
        assert "RuntimeError" in emitted_events[1]["run"]["facets"]["errorMessage"]["message"]
        assert "stackTrace" in emitted_events[1]["run"]["facets"]["errorMessage"]
