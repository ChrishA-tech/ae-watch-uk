"""Medallion Ingestion Pipeline Integration and Unit Tests.

Validates NHS England A&E, UKHSA Data Dashboard, and Open-Meteo ingestion pipelines,
explicitly asserting benchmark data for Liverpool University Hospitals NHS FT (REM).
Author: CHRISH PEP FELIX A
"""

import httpx
import pytest
import respx

from ae_watch.ingestion.nhs_ae_loader import nhs_ae_loader, parse_period_date
from ae_watch.ingestion.ukhsa_client import ukhsa_client
from ae_watch.ingestion.weather_client import weather_client

SAMPLE_NHS_CSV = """Period,Org Code,Parent Org,Org name,A&E attendances Type 1,A&E attendances Type 2,A&E attendances Other A&E Department,A&E attendances Booked Appointments Type 1,A&E attendances Booked Appointments Type 2,A&E attendances Booked Appointments Other Department,Attendances over 4hrs Type 1,Attendances over 4hrs Type 2,Attendances over 4hrs Other Department,Attendances over 4hrs Booked Appointments Type 1,Attendances over 4hrs Booked Appointments Type 2,Attendances over 4hrs Booked Appointments Other Department,Patients who have waited 4-12 hs from DTA to admission,Patients who have waited 12+ hrs from DTA to admission,Emergency admissions via A&E - Type 1,Emergency admissions via A&E - Type 2,Emergency admissions via A&E - Other A&E department,Other emergency admissions
MSitAE-MARCH-2024,REM,NHS ENGLAND NORTH WEST ,LIVERPOOL UNIVERSITY HOSPITALS NHS FOUNDATION TRUST,17661,197,8835,430,0,0,7801,0,576,59,0,0,2226,1390,5318,0,0,2577
MSitAE-MARCH-2024,RJR,NHS ENGLAND NORTH WEST ,COUNTESS OF CHESTER HOSPITAL NHS FOUNDATION TRUST,6341,0,986,0,0,0,3367,0,126,0,0,0,339,631,1761,0,0,1257
"""


def test_parse_period_date():
    """Verify parsing of NHS England period string."""
    d = parse_period_date("MSitAE-MARCH-2024")
    assert d.year == 2024
    assert d.month == 3
    assert d.day == 1


def test_parse_nhs_csv_records():
    """Verify that sample NHS CSV text correctly parses Liverpool Trust (REM)."""
    records = nhs_ae_loader.parse_csv_to_records(SAMPLE_NHS_CSV, "test.csv")
    assert len(records) == 2

    rem_rec = next(r for r in records if r.org_code == "REM")
    assert rem_rec.org_code == "REM"
    assert rem_rec.type1_attendances == 17661
    assert rem_rec.type1_over4hr == 7801
    assert rem_rec.over12hr_trolley_waits == 1390
    assert rem_rec.emergency_admissions == 5318


@pytest.mark.asyncio
async def test_ukhsa_fetch_metric_records_mocked():
    """Verify UKHSA client extracts structured pathogen records."""
    mock_data = {
        "results": [
            {
                "theme": "infectious_disease",
                "sub_theme": "respiratory",
                "topic": "Influenza",
                "geography_type": "Nation",
                "geography": "England",
                "geography_code": "E92000001",
                "metric": "influenza_healthcare_hospitalAdmissionRateByWeek",
                "metric_value": 4.52,
                "date": "2024-01-15",
            }
        ],
        "next": None,
    }

    path = "/themes/infectious_disease/sub_themes/respiratory/topics/Influenza/geography_types/Nation/geographies/England/metrics/influenza_healthcare_hospitalAdmissionRateByWeek"
    url = f"https://api.ukhsa-dashboard.data.gov.uk{path}?page_size=100"

    with respx.mock(assert_all_called=True) as router:
        router.get(url).respond(200, json=mock_data)

        async with httpx.AsyncClient() as client:
            records = await ukhsa_client.fetch_metric_records(client, path, max_pages=1)
            assert len(records) == 1
            assert records[0].topic == "Influenza"
            assert records[0].metric_value == 4.52
            assert records[0].geography_name == "England"


@pytest.mark.asyncio
async def test_weather_fetch_site_records_mocked():
    """Verify Open-Meteo client parses historical weather archive."""
    mock_data = {
        "daily": {
            "time": ["2024-01-15", "2024-01-16"],
            "temperature_2m_max": [4.0, -1.0],
            "temperature_2m_min": [-2.0, -5.0],
            "temperature_2m_mean": [1.0, -3.0],
            "apparent_temperature_min": [-4.5, -8.0],
            "wind_speed_10m_max": [25.0, 30.0],
            "precipitation_sum": [0.0, 2.5],
        }
    }

    site = {
        "trust_code": "REM",
        "hospital_name": "Royal Liverpool University Hospital",
        "latitude": 53.4093,
        "longitude": -2.9566,
    }

    with respx.mock(assert_all_called=True) as router:
        router.get("https://archive-api.open-meteo.com/v1/archive").respond(200, json=mock_data)

        async with httpx.AsyncClient() as client:
            records = await weather_client.fetch_weather_for_site(
                client, site, "2024-01-15", "2024-01-16"
            )
            assert len(records) == 2
            assert records[0].trust_code == "REM"
            assert records[0].temp_min_c == -2.0
            assert records[0].temp_mean_c == 1.0
            assert records[1].temp_min_c == -5.0
