FROM pgvector/pgvector:pg16

LABEL maintainer="CHRISH PEP FELIX A"
LABEL description="PostgreSQL 16 with pgvector and PostGIS 3 for AE-Watch UK"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       postgresql-16-postgis-3 \
       postgresql-16-postgis-3-scripts \
    && rm -rf /var/lib/apt/lists/*
