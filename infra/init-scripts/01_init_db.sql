-- AE-Watch UK Database Initialization Script
-- Author: CHRISH PEP FELIX A

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

-- Medallion & Governance Schemas
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS quarantine;

-- Dead-Letter Quarantine Table with Full Column-Level Error Diagnostics
CREATE TABLE IF NOT EXISTS quarantine.ingestion_errors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_pipeline VARCHAR(64) NOT NULL,
    trust_code VARCHAR(16),
    raw_payload JSONB NOT NULL,
    error_diagnostics JSONB NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quarantine_pipeline ON quarantine.ingestion_errors (source_pipeline);
CREATE INDEX IF NOT EXISTS idx_quarantine_trust ON quarantine.ingestion_errors (trust_code);
CREATE INDEX IF NOT EXISTS idx_quarantine_ingested_at ON quarantine.ingestion_errors (ingested_at);

-- Bronze Raw Tables
CREATE TABLE IF NOT EXISTS bronze.nhs_ae_raw (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    period_date DATE NOT NULL,
    org_code VARCHAR(16) NOT NULL,
    org_name VARCHAR(255) NOT NULL,
    type1_attendances INTEGER,
    type2_attendances INTEGER,
    type3_attendances INTEGER,
    total_attendances INTEGER NOT NULL,
    type1_over4hr INTEGER,
    total_over4hr INTEGER NOT NULL,
    emergency_admissions INTEGER,
    over12hr_trolley_waits INTEGER,
    raw_source_file VARCHAR(255) NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bronze_nhs_org ON bronze.nhs_ae_raw (org_code, period_date);

CREATE TABLE IF NOT EXISTS bronze.ukhsa_pathogens_raw (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    theme VARCHAR(64) NOT NULL,
    sub_theme VARCHAR(64) NOT NULL,
    topic VARCHAR(64) NOT NULL,
    metric VARCHAR(128) NOT NULL,
    geography_type VARCHAR(64) NOT NULL,
    geography_name VARCHAR(128) NOT NULL,
    geography_code VARCHAR(32),
    metric_value DOUBLE PRECISION NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bronze_ukhsa_metric ON bronze.ukhsa_pathogens_raw (topic, metric, period_start);

CREATE TABLE IF NOT EXISTS bronze.open_meteo_raw (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trust_code VARCHAR(16) NOT NULL,
    hospital_name VARCHAR(255) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    record_date DATE NOT NULL,
    temp_min_c DOUBLE PRECISION,
    temp_mean_c DOUBLE PRECISION,
    temp_max_c DOUBLE PRECISION,
    apparent_temp_min_c DOUBLE PRECISION,
    wind_speed_max_kmh DOUBLE PRECISION,
    precipitation_sum_mm DOUBLE PRECISION,
    is_forecast BOOLEAN NOT NULL DEFAULT FALSE,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bronze_meteo_trust ON bronze.open_meteo_raw (trust_code, record_date);
