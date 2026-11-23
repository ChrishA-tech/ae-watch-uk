"""Schema Validation and Dead-Letter Quarantine Tests.

Enforces that malformed rows failing Pydantic validation are safely routed to
quarantine.ingestion_errors with full column-level error diagnostics rather than crashing batch loads.
Author: CHRISH PEP FELIX A
"""

from datetime import date

import psycopg

from ae_watch.config import settings
from ae_watch.ingestion.quarantine import quarantine_handler
from ae_watch.ingestion.schemas import (
    NHSAttendanceRecord,
    OpenMeteoWeatherRecord,
    UKHSAPathogenRecord,
)


def test_valid_nhs_record_passes_contract():
    """Verify that a compliant NHS England record passes validation."""
    payload = {
        "period_date": date(2024, 3, 1),
        "org_code": "REM",
        "org_name": "LIVERPOOL UNIVERSITY HOSPITALS NHS FOUNDATION TRUST",
        "type1_attendances": 17661,
        "type2_attendances": 197,
        "type3_attendances": 8835,
        "total_attendances": 26693,
        "type1_over4hr": 7801,
        "total_over4hr": 8377,
        "emergency_admissions": 5318,
        "over12hr_trolley_waits": 1390,
        "raw_source_file": "March-2024.csv",
    }
    record = quarantine_handler.validate_or_quarantine(
        NHSAttendanceRecord,
        payload,
        source_pipeline="test_nhs",
        trust_code_key="org_code",
    )
    assert record is not None
    assert record.org_code == "REM"
    assert record.total_attendances == 26693


def test_corrupted_nhs_record_routed_to_quarantine(clean_quarantine_table):
    """Verify corrupted NHS records (total breaches > total attendances) route to quarantine with diagnostics."""
    invalid_payload = {
        "period_date": date(2024, 3, 1),
        "org_code": "REM",
        "org_name": "LIVERPOOL UNIVERSITY HOSPITALS NHS FOUNDATION TRUST",
        "type1_attendances": 100,
        "total_attendances": 500,
        "type1_over4hr": 200,  # Invalid: type1_over4hr > type1_attendances
        "total_over4hr": 999,  # Invalid: total_over4hr > total_attendances
        "raw_source_file": "corrupted.csv",
    }

    result = quarantine_handler.validate_or_quarantine(
        NHSAttendanceRecord,
        invalid_payload,
        source_pipeline="test_nhs_corrupted",
        trust_code_key="org_code",
    )
    # Batch load does not crash; invalid row returns None
    assert result is None

    # Verify dead-letter table received the error with column diagnostics
    with psycopg.connect(settings.postgres_connection_uri) as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT source_pipeline, trust_code, error_diagnostics, raw_payload
                FROM quarantine.ingestion_errors
                WHERE source_pipeline = 'test_nhs_corrupted'
                """
        )
        rows = cur.fetchall()
        assert len(rows) == 1
        source, trust, diags, _raw = rows[0]
        assert source == "test_nhs_corrupted"
        assert trust == "REM"
        assert len(diags) > 0
        assert any("total_over4hr" in d["error_message"] for d in diags)


def test_corrupted_ukhsa_record_routed_to_quarantine(clean_quarantine_table):
    """Verify UKHSA records with inverted dates route to dead-letter quarantine."""
    invalid_payload = {
        "theme": "infectious_disease",
        "sub_theme": "respiratory",
        "topic": "Influenza",
        "metric": "influenza_testing_positivityByWeek",
        "geography_type": "Nation",
        "geography_name": "England",
        "geography_code": "E92000001",
        "metric_value": -5.0,  # Invalid: negative rate
        "period_start": date(2024, 2, 10),
        "period_end": date(2024, 2, 1),  # Invalid: start > end
    }

    result = quarantine_handler.validate_or_quarantine(
        UKHSAPathogenRecord,
        invalid_payload,
        source_pipeline="test_ukhsa_corrupted",
        trust_code_key="geography_code",
    )
    assert result is None

    with psycopg.connect(settings.postgres_connection_uri) as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT error_diagnostics
                FROM quarantine.ingestion_errors
                WHERE source_pipeline = 'test_ukhsa_corrupted'
                """
        )
        rows = cur.fetchall()
        assert len(rows) == 1
        diags = rows[0][0]
        assert any("greater_than_equal" in d["error_type"] for d in diags)


def test_corrupted_weather_temperatures_routed_to_quarantine(clean_quarantine_table):
    """Verify weather records where temp_min > temp_max route to quarantine."""
    invalid_payload = {
        "trust_code": "REM",
        "hospital_name": "Royal Liverpool University Hospital",
        "latitude": 53.4093,
        "longitude": -2.9566,
        "record_date": date(2024, 1, 15),
        "temp_min_c": 15.0,  # Invalid: min > max
        "temp_mean_c": 5.0,
        "temp_max_c": 2.0,
        "is_forecast": False,
    }

    result = quarantine_handler.validate_or_quarantine(
        OpenMeteoWeatherRecord,
        invalid_payload,
        source_pipeline="test_weather_corrupted",
        trust_code_key="trust_code",
    )
    assert result is None

    with psycopg.connect(settings.postgres_connection_uri) as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT error_diagnostics
                FROM quarantine.ingestion_errors
                WHERE source_pipeline = 'test_weather_corrupted'
                """
        )
        rows = cur.fetchall()
        assert len(rows) == 1
        diags = rows[0][0]
        assert any("temp_min_c" in d["error_message"] for d in diags)
