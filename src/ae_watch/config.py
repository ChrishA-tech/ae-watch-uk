"""Configuration management for AE-Watch UK.

Loads settings from environment variables and root .env file.
Author: CHRISH PEP FELIX A
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root directory of the repository
ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Core application settings for AE-Watch UK."""

    # Author metadata
    author: str = "CHRISH PEP FELIX A"
    project_name: str = "ae-watch-uk"

    # Gemini Free-Tier Models & API
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_reasoning_model: str = Field(default="gemini-3.8-flash", alias="GEMINI_REASONING_MODEL")
    gemini_fast_model: str = Field(default="gemini-3.5-flash-lite", alias="GEMINI_FAST_MODEL")
    gemini_embedding_model: str = Field(
        default="gemini-embedding-2", alias="GEMINI_EMBEDDING_MODEL"
    )

    # PostgreSQL 16 + PostGIS + pgvector
    postgres_user: str = Field(default="aewatch", alias="POSTGRES_USER")
    postgres_password: str = Field(default="aewatchpass2026", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="aewatch_db", alias="POSTGRES_DB")

    # Marquez & OpenLineage Telemetry
    openlineage_url: str = Field(default="http://localhost:5002", alias="OPENLINEAGE_URL")
    openlineage_namespace: str = Field(default="ae-watch-uk", alias="OPENLINEAGE_NAMESPACE")

    # Neo4j Community
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="aewatchpass2026", alias="NEO4J_PASSWORD")

    # Target Benchmark Trust: Liverpool University Hospitals NHS FT (ODS: REM)
    benchmark_trust_ods: str = "REM"
    benchmark_trust_name: str = "Liverpool University Hospitals NHS Foundation Trust"

    # Cheshire & Merseyside ICB Trust ODS Codes
    cheshire_merseyside_trust_ods: list[str] = [
        "REM",  # Liverpool University Hospitals
        "RJR",  # Mersey and West Lancashire Teaching Hospitals
        "RBL",  # Wirral University Teaching Hospital
        "RWW",  # Warrington and Halton Teaching Hospitals
        "RBS",  # Alder Hey Children's NHS FT
        "REP",  # Liverpool Women's NHS FT
        "RBN",  # St Helens and Knowsley Teaching Hospitals (historical / merged into RJR)
    ]

    # Directories
    data_dir: Path = ROOT_DIR / "data"
    bronze_dir: Path = ROOT_DIR / "data" / "bronze"
    silver_dir: Path = ROOT_DIR / "data" / "silver"
    quarantine_dir: Path = ROOT_DIR / "data" / "quarantine"

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def postgres_connection_uri(self) -> str:
        """Construct PostgreSQL connection string."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
