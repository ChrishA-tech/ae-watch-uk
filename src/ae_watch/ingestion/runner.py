"""Unified Ingestion Orchestration Runner for AE-Watch UK.

Author: CHRISH PEP FELIX A
"""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from ae_watch.ingestion.nhs_ae_loader import nhs_ae_loader
from ae_watch.ingestion.ukhsa_client import ukhsa_client
from ae_watch.ingestion.weather_client import weather_client
from ae_watch.utils.logger import logger

app = typer.Typer(
    help="AE-Watch UK Medallion Ingestion Runner (Author: CHRISH PEP FELIX A)",
    add_completion=False,
)
console = Console()


@app.command()
def nhs():
    """Ingest real NHS England A&E monthly attendances & emergency admissions."""
    console.print("[bold cyan]Starting NHS England A&E Ingestion...[/bold cyan]")
    count = asyncio.run(nhs_ae_loader.run())
    console.print(
        f"[bold green]Successfully ingested {count} NHS A&E records into Bronze![/bold green]"
    )


@app.command()
def ukhsa():
    """Ingest UKHSA Norovirus, Influenza, and RSV metrics from public API."""
    console.print("[bold cyan]Starting UKHSA Surveillance Ingestion...[/bold cyan]")
    count = asyncio.run(ukhsa_client.run())
    console.print(
        f"[bold green]Successfully ingested {count} UKHSA surveillance records into Bronze![/bold green]"
    )


@app.command()
def weather():
    """Ingest Open-Meteo telemetry mapped to NHS Trust coordinates."""
    console.print("[bold cyan]Starting Open-Meteo Weather Ingestion...[/bold cyan]")
    count = asyncio.run(weather_client.run())
    console.print(
        f"[bold green]Successfully ingested {count} Weather records into Bronze![/bold green]"
    )


@app.command()
def all():
    """Execute all medallion ingestion pipelines sequentially with OpenLineage telemetry."""
    console.print("[bold magenta]==================================================[/bold magenta]")
    console.print("[bold magenta]   AE-Watch UK Medallion Ingestion Pipeline       [/bold magenta]")
    console.print("[bold magenta]   Author: CHRISH PEP FELIX A                     [/bold magenta]")
    console.print("[bold magenta]==================================================[/bold magenta]")

    async def _run_all():
        logger.info("ingestion_orchestration_started")
        n_count = await nhs_ae_loader.run()
        u_count = await ukhsa_client.run()
        w_count = await weather_client.run()
        return n_count, u_count, w_count

    n_count, u_count, w_count = asyncio.run(_run_all())

    table = Table(title="Medallion Bronze Ingestion Summary")
    table.add_column("Pipeline Source", style="cyan", no_wrap=True)
    table.add_column("Target Schema Table", style="yellow")
    table.add_column("Records Landed", style="green", justify="right")
    table.add_row("NHS England A&E (MSitAE)", "bronze.nhs_ae_raw", str(n_count))
    table.add_row("UKHSA Data Dashboard", "bronze.ukhsa_pathogens_raw", str(u_count))
    table.add_row("Open-Meteo Weather", "bronze.open_meteo_raw", str(w_count))
    table.add_section()
    table.add_row("Total Bronze Records", "", str(n_count + u_count + w_count))
    console.print(table)


if __name__ == "__main__":
    app()
