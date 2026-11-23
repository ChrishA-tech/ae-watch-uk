"""Knowledge Graph Populator and Query Engine for AE-Watch UK.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

from typing import Any

import psycopg

from ae_watch.config import settings
from ae_watch.features.spatial import TRUST_CENTROIDS, compute_trust_distance_matrix
from ae_watch.graph.client import Neo4jGraphClient, graph_client
from ae_watch.graph.schema import init_graph_schema, seed_ontology_nodes
from ae_watch.utils.logger import logger


class ClinicalKnowledgeGraphPopulator:
    """Populates and updates Neo4j with Trust operational topologies and live forecast states."""

    def __init__(self, client: Neo4jGraphClient = graph_client):
        self.client = client

    def sync_trusts_and_proximity(self) -> int:
        """Create Trust nodes and pairwise proximity relationships within 25 km."""
        logger.info("syncing_trust_topologies_and_proximity")
        distances = compute_trust_distance_matrix()

        # 1. Create Trust nodes and connect to ICB QE1
        for ods, meta in TRUST_CENTROIDS.items():
            query = """
            MERGE (t:Trust {ods_code: $ods_code})
            SET t.name = $name,
                t.latitude = $lat,
                t.longitude = $lon,
                t.is_benchmark = ($ods_code = 'REM'),
                t.icb_code = 'QE1'
            WITH t
            MATCH (icb:ICB {code: 'QE1'})
            MERGE (t)-[:LOCATED_IN_ICB]->(icb);
            """
            self.client.run_query(
                query,
                {"ods_code": ods, "name": meta["name"], "lat": meta["lat"], "lon": meta["lon"]},
            )

        # 2. Create Proximity relationships within 25km
        proximity_count = 0
        for (t1, t2), dist in distances.items():
            if t1 != t2 and 0.0 < dist <= 25.0:
                idw_w = round(1.0 / dist, 4)
                query = """
                MATCH (a:Trust {ods_code: $t1})
                MATCH (b:Trust {ods_code: $t2})
                MERGE (a)-[r:PROXIMATE_TO]->(b)
                SET r.distance_km = $dist,
                    r.idw_weight = $idw_w;
                """
                self.client.run_query(query, {"t1": t1, "t2": t2, "dist": dist, "idw_w": idw_w})
                proximity_count += 1

        logger.info("trust_proximity_synced", proximity_edges=proximity_count)
        return len(TRUST_CENTROIDS)

    def sync_live_forecast_and_causal_states(self) -> int:
        """Fetch latest Gold Mart features and update Trust node operational states."""
        logger.info("syncing_live_forecast_and_causal_states_from_postgres")

        query_pg = """
        SELECT DISTINCT ON (trust_code)
            trust_code,
            period_date,
            breach_4hr_pct,
            target_breach_rate_horizon_7d,
            target_surge_binary_7d,
            total_attendances,
            total_cold_snap_degree_days,
            h3_res7_cell,
            idw_neighbor_breach_rate
        FROM gold.ml_trust_forecast_features
        ORDER BY trust_code, period_date DESC;
        """

        with psycopg.connect(settings.postgres_connection_uri) as conn, conn.cursor() as cur:
            cur.execute(query_pg)
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]

        records = [dict(zip(cols, r)) for r in rows]
        updated_count = 0

        for rec in records:
            trust_code = rec["trust_code"]
            breach_pct = float(rec["breach_4hr_pct"] or 0.0)
            pred_7d = float(rec["target_breach_rate_horizon_7d"] or breach_pct)
            surge_flag = int(rec["target_surge_binary_7d"] or 0)
            cold_degree_days = float(rec["total_cold_snap_degree_days"] or 0.0)
            h3_cell = str(rec["h3_res7_cell"] or "871951071ffffff")

            # Determine OPEL tier based on breach severity
            if breach_pct >= 45.0:
                opel_tier = 4
            elif breach_pct >= 30.0:
                opel_tier = 3
            elif breach_pct >= 20.0:
                opel_tier = 2
            else:
                opel_tier = 1

            # Determine UKHSA Alert level from cold degree days
            if cold_degree_days >= 30.0:
                alert_code = "Red"
            elif cold_degree_days >= 20.0:
                alert_code = "Amber"
            elif cold_degree_days >= 10.0:
                alert_code = "Yellow"
            else:
                alert_code = "Green"

            # DiD estimated causal breach increase under cold alert (+2.058%)
            cold_alert_impact = 2.058 if alert_code in ("Amber", "Red") else 0.0

            cypher_update = """
            MATCH (t:Trust {ods_code: $trust_code})
            SET t.latest_breach_rate = $breach_pct,
                t.predicted_7d_breach = $pred_7d,
                t.surge_risk = $surge_flag,
                t.cold_snap_degree_days = $cold_degree_days,
                t.h3_cell = $h3_cell,
                t.cold_alert_impact_pct = $cold_alert_impact,
                t.last_period_date = $period_date

            WITH t
            MATCH (o:OPEL {level: $opel_tier})
            MATCH (a:AlertLevel {code: $alert_code})

            // Replace current escalation relationships
            OPTIONAL MATCH (t)-[r_old_opel:CURRENT_ESCALATION_LEVEL]->(:OPEL)
            DELETE r_old_opel
            MERGE (t)-[:CURRENT_ESCALATION_LEVEL]->(o)

            WITH t, a
            OPTIONAL MATCH (t)-[r_old_alert:CURRENT_WEATHER_ALERT]->(:AlertLevel)
            DELETE r_old_alert
            MERGE (t)-[:CURRENT_WEATHER_ALERT]->(a);
            """

            self.client.run_query(
                cypher_update,
                {
                    "trust_code": trust_code,
                    "breach_pct": breach_pct,
                    "pred_7d": pred_7d,
                    "surge_flag": surge_flag,
                    "cold_degree_days": cold_degree_days,
                    "h3_cell": h3_cell,
                    "cold_alert_impact": cold_alert_impact,
                    "period_date": str(rec["period_date"]),
                    "opel_tier": opel_tier,
                    "alert_code": alert_code,
                },
            )
            updated_count += 1

        logger.info("live_forecast_states_synced_to_neo4j", updated_trusts=updated_count)
        return updated_count

    def populate_full_graph(self) -> dict[str, Any]:
        """Execute complete schema init, ontology seeding, and live state sync."""
        init_graph_schema(self.client)
        seed_ontology_nodes(self.client)
        trusts_synced = self.sync_trusts_and_proximity()
        states_synced = self.sync_live_forecast_and_causal_states()
        return {
            "trusts_synced": trusts_synced,
            "states_synced": states_synced,
            "status": "ready",
        }

    def traverse_catchment_escalation(self, trust_ods: str = "REM") -> dict[str, Any]:
        """Traverse multi-hop graph to extract operational pressure and mandatory interventions."""
        query = """
        MATCH (t:Trust {ods_code: $ods})
        OPTIONAL MATCH (t)-[:CURRENT_ESCALATION_LEVEL]->(opel:OPEL)
        OPTIONAL MATCH (t)-[:CURRENT_WEATHER_ALERT]->(alert:AlertLevel)
        OPTIONAL MATCH (opel)-[:MANDATES_INTERVENTION|RECOMMENDS_INTERVENTION]->(inv_opel:Intervention)
        OPTIONAL MATCH (alert)-[:MANDATES_INTERVENTION|RECOMMENDS_INTERVENTION]->(inv_alert:Intervention)

        WITH t, opel, alert, collect(DISTINCT inv_opel.name) + collect(DISTINCT inv_alert.name) AS interventions

        OPTIONAL MATCH (t)-[p:PROXIMATE_TO]->(n:Trust)
        OPTIONAL MATCH (n)-[:CURRENT_ESCALATION_LEVEL]->(n_opel:OPEL)

        RETURN t.ods_code AS trust_code,
               t.name AS trust_name,
               t.latest_breach_rate AS latest_breach_rate,
               t.predicted_7d_breach AS predicted_7d_breach,
               t.surge_risk AS surge_risk,
               t.cold_alert_impact_pct AS cold_alert_impact_pct,
               opel.level AS opel_level,
               opel.name AS opel_name,
               alert.code AS weather_alert_code,
               interventions AS active_interventions,
               collect(DISTINCT {
                   neighbor_code: n.ods_code,
                   neighbor_name: n.name,
                   distance_km: p.distance_km,
                   neighbor_breach: n.latest_breach_rate,
                   neighbor_opel: n_opel.level
               }) AS proximate_neighbors;
        """
        results = self.client.run_query(query, {"ods": trust_ods.upper()})
        return results[0] if results else {}


graph_populator = ClinicalKnowledgeGraphPopulator()
