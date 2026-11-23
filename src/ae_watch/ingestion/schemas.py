"""Pydantic v2 data validation schemas and data contracts.

Enforces boundary contracts for NHS England A&E, UKHSA, and Open-Meteo feeds.
Author: CHRISH PEP FELIX A
"""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ColumnErrorDiagnostic(BaseModel):
    """Structured column-level error diagnostic for dead-letter routing."""

    field_name: str
    error_type: str
    error_message: str
    input_value: Any = None


class NHSAttendanceRecord(BaseModel):
    """Pydantic contract for NHS England A&E Provider attendances."""

    period_date: date
    org_code: str = Field(min_length=3, max_length=10)
    org_name: str = Field(min_length=2, max_length=255)
    type1_attendances: int | None = Field(default=None, ge=0)
    type2_attendances: int | None = Field(default=None, ge=0)
    type3_attendances: int | None = Field(default=None, ge=0)
    total_attendances: int = Field(ge=0)
    type1_over4hr: int | None = Field(default=None, ge=0)
    total_over4hr: int = Field(ge=0)
    emergency_admissions: int | None = Field(default=None, ge=0)
    over12hr_trolley_waits: int | None = Field(default=None, ge=0)
    raw_source_file: str = Field(min_length=1)

    @field_validator("org_code")
    @classmethod
    def clean_org_code(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Organisation code cannot be empty")
        return cleaned

    @model_validator(mode="after")
    def validate_breach_bounds(self) -> "NHSAttendanceRecord":
        if self.total_over4hr > self.total_attendances:
            raise ValueError(
                f"total_over4hr ({self.total_over4hr}) cannot exceed total_attendances ({self.total_attendances})"
            )
        if (
            self.type1_attendances is not None
            and self.type1_over4hr is not None
            and self.type1_over4hr > self.type1_attendances
        ):
            raise ValueError(
                f"type1_over4hr ({self.type1_over4hr}) cannot exceed type1_attendances ({self.type1_attendances})"
            )
        return self


class UKHSAPathogenRecord(BaseModel):
    """Pydantic contract for UKHSA Data Dashboard surveillance metrics."""

    theme: str = Field(min_length=1, max_length=64)
    sub_theme: str = Field(min_length=1, max_length=64)
    topic: str = Field(min_length=1, max_length=64)
    metric: str = Field(min_length=1, max_length=128)
    geography_type: str = Field(min_length=1, max_length=64)
    geography_name: str = Field(min_length=1, max_length=128)
    geography_code: str | None = Field(default=None, max_length=32)
    metric_value: float = Field(ge=0.0)
    period_start: date
    period_end: date

    @model_validator(mode="after")
    def validate_period_dates(self) -> "UKHSAPathogenRecord":
        if self.period_start > self.period_end:
            raise ValueError(
                f"period_start ({self.period_start}) cannot be after period_end ({self.period_end})"
            )
        return self


class OpenMeteoWeatherRecord(BaseModel):
    """Pydantic contract for Open-Meteo Trust-mapped weather observations."""

    trust_code: str = Field(min_length=3, max_length=10)
    hospital_name: str = Field(min_length=2, max_length=255)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    record_date: date
    temp_min_c: float | None = Field(default=None, ge=-50.0, le=60.0)
    temp_mean_c: float | None = Field(default=None, ge=-50.0, le=60.0)
    temp_max_c: float | None = Field(default=None, ge=-50.0, le=60.0)
    apparent_temp_min_c: float | None = Field(default=None, ge=-60.0, le=60.0)
    wind_speed_max_kmh: float | None = Field(default=None, ge=0.0, le=300.0)
    precipitation_sum_mm: float | None = Field(default=None, ge=0.0, le=500.0)
    is_forecast: bool = False

    @model_validator(mode="after")
    def validate_temperatures(self) -> "OpenMeteoWeatherRecord":
        if (
            self.temp_min_c is not None
            and self.temp_max_c is not None
            and self.temp_min_c > self.temp_max_c
        ):
            raise ValueError(
                f"temp_min_c ({self.temp_min_c}) cannot be greater than temp_max_c ({self.temp_max_c})"
            )
        return self
