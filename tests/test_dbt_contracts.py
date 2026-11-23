"""Data Contract and Medallion Integration Tests.

Validates that transformed Silver and Gold dbt tables meet strict data contracts
and verify clinical pressure indicators for Liverpool University Hospitals NHS FT (REM).
Author: CHRISH PEP FELIX A
"""



def test_silver_nhs_ae_contracts(db_conn):
    """Verify Silver A&E performance percentage constraints and REM presence."""
    with db_conn.cursor() as cur:
        # 1. Performance percentage must be between 0 and 100
        cur.execute(
            """
            SELECT COUNT(*)
            FROM silver.stg_nhs_ae_attendances
            WHERE performance_4hr_pct < 0.0 OR performance_4hr_pct > 100.0;
            """
        )
        violations = cur.fetchone()[0]
        assert violations == 0

        # 2. Liverpool Trust (REM) must be present in Silver
        cur.execute(
            """
            SELECT COUNT(*)
            FROM silver.stg_nhs_ae_attendances
            WHERE org_code = 'REM';
            """
        )
        rem_count = cur.fetchone()[0]
        assert rem_count >= 5


def test_silver_weather_cold_snap_contracts(db_conn):
    """Verify Silver weather cold-snap degree days are strictly non-negative."""
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM silver.stg_weather_daily
            WHERE cold_snap_degree_days < 0.0;
            """
        )
        violations = cur.fetchone()[0]
        assert violations == 0


def test_gold_feature_mart_benchmarks(db_conn):
    """Verify Gold winter pressure feature mart for Liverpool Trust (REM)."""
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT period_date, trust_code, performance_4hr_pct, breach_4hr_pct,
                   total_cold_snap_degree_days, operational_pressure_level
            FROM gold.fct_trust_winter_pressure_daily
            WHERE trust_code = 'REM'
            ORDER BY period_date DESC;
            """
        )
        rows = cur.fetchall()
        assert len(rows) >= 5

        # Check Liverpool Trust winter peak metrics
        for row in rows:
            _period, trust, perf, breach, cold_days, pressure = row
            assert trust == "REM"
            assert 0.0 <= float(perf) <= 100.0
            assert 0.0 <= float(breach) <= 100.0
            assert float(cold_days) >= 0.0
            assert pressure in {"NORMAL", "ELEVATED", "SEVERE", "CRITICAL"}
