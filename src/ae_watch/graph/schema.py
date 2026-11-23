"""Neo4j Graph Schema and Constraint Definitions for AE-Watch UK.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

from ae_watch.graph.client import Neo4jGraphClient, graph_client
from ae_watch.utils.logger import logger


def init_graph_schema(client: Neo4jGraphClient = graph_client) -> None:
    """Create uniqueness constraints and indexes in Neo4j."""
    logger.info("initializing_neo4j_graph_schema")

    constraints = [
        "CREATE CONSTRAINT trust_ods_unique IF NOT EXISTS FOR (t:Trust) REQUIRE t.ods_code IS UNIQUE;",
        "CREATE CONSTRAINT icb_code_unique IF NOT EXISTS FOR (i:ICB) REQUIRE i.code IS UNIQUE;",
        "CREATE CONSTRAINT opel_level_unique IF NOT EXISTS FOR (o:OPEL) REQUIRE o.level IS UNIQUE;",
        "CREATE CONSTRAINT alert_code_unique IF NOT EXISTS FOR (a:AlertLevel) REQUIRE a.code IS UNIQUE;",
        "CREATE CONSTRAINT intervention_name_unique IF NOT EXISTS FOR (v:Intervention) REQUIRE v.name IS UNIQUE;",
    ]

    for c in constraints:
        client.run_query(c)

    logger.info("neo4j_schema_constraints_verified")


def seed_ontology_nodes(client: Neo4jGraphClient = graph_client) -> None:
    """Populate baseline Integrated Care Board, OPEL tiers, UKHSA alerts, and UEC interventions."""
    logger.info("seeding_neo4j_clinical_operations_ontology")

    statements = [
        # 1. Integrated Care Board
        """
        MERGE (icb:ICB {code: 'QE1'})
        ON CREATE SET icb.name = 'NHS Cheshire and Merseyside Integrated Care Board',
                      icb.region = 'North West',
                      icb.population = 2700000
        """,
        # 2. OPEL Escalation Tiers
        """
        MERGE (opel1:OPEL {level: 1})
        ON CREATE SET opel1.name = 'OPEL 1', opel1.description = 'Normal operating capacity within standard resources'
        """,
        """
        MERGE (opel2:OPEL {level: 2})
        ON CREATE SET opel2.name = 'OPEL 2', opel2.description = 'Moderate pressure with emerging bed constraints or handover delays'
        """,
        """
        MERGE (opel3:OPEL {level: 3})
        ON CREATE SET opel3.name = 'OPEL 3', opel3.description = 'Severe pressure with major bed occupancy and emergency breach risk'
        """,
        """
        MERGE (opel4:OPEL {level: 4})
        ON CREATE SET opel4.name = 'OPEL 4', opel4.description = 'Critical operational pressure unable to deliver comprehensive care'
        """,
        # 3. UKHSA Cold Health Alert Levels
        """
        MERGE (c_green:AlertLevel {code: 'Green'})
        ON CREATE SET c_green.name = 'Green Alert', c_green.severity = 0, c_green.description = 'No active cold weather warning'
        """,
        """
        MERGE (c_yellow:AlertLevel {code: 'Yellow'})
        ON CREATE SET c_yellow.name = 'Yellow Alert', c_yellow.severity = 1, c_yellow.description = 'Minor impacts on vulnerable populations'
        """,
        """
        MERGE (c_amber:AlertLevel {code: 'Amber'})
        ON CREATE SET c_amber.name = 'Amber Alert', c_amber.severity = 2, c_amber.description = 'Enhanced weather health alert with significant NHS service strain'
        """,
        """
        MERGE (c_red:AlertLevel {code: 'Red'})
        ON CREATE SET c_red.name = 'Red Alert', c_red.severity = 3, c_red.description = 'Severe cold weather emergency with acute systemic disruption'
        """,
        # 4. NHS Urgent & Emergency Care Interventions
        """
        MERGE (sdec:Intervention {name: 'SDEC'})
        ON CREATE SET sdec.full_name = 'Same Day Emergency Care',
                      sdec.category = 'Ambulant Diversion',
                      sdec.standard = 'Assess and treat emergency medical and surgical patients without overnight bed admission',
                      sdec.target_diversion_pct = 30.0
        """,
        """
        MERGE (utc:Intervention {name: 'UTC'})
        ON CREATE SET utc.full_name = 'Urgent Treatment Centre',
                      utc.category = 'Primary Care Co-location',
                      utc.standard = 'Divert Type 3 and minor illness/injury from main Type 1 A&E departments',
                      utc.target_diversion_pct = 20.0
        """,
        """
        MERGE (vw:Intervention {name: 'Virtual_Ward'})
        ON CREATE SET vw.full_name = 'Virtual Ward / Hospital-at-Home',
                      vw.category = 'Community Step-down',
                      vw.standard = 'Remote continuous physiological telemetry and clinical reviews for frailty and respiratory patients',
                      vw.target_bed_equivalents = 50
        """,
        """
        MERGE (spoa:Intervention {name: 'SPoA'})
        ON CREATE SET spoa.full_name = 'Single Point of Access',
                      spoa.category = 'System Flow Coordination',
                      spoa.standard = 'Centralized ICB coordination of discharge to assess and community social care beds'
        """,
        """
        MERGE (amb:Intervention {name: 'Ambulance_Handover_45Min'})
        ON CREATE SET amb.full_name = '45-Minute Ambulance Handover Escalation Protocol',
                      amb.category = 'Emergency Handover Flow',
                      amb.standard = 'Immediate hospital leadership presence in emergency department when ambulance waits exceed 45 minutes'
        """,
        # 5. Connect OPEL tiers to interventions
        """
        MATCH (opel2:OPEL {level: 2}), (sdec:Intervention {name: 'SDEC'}), (utc:Intervention {name: 'UTC'})
        MERGE (opel2)-[:RECOMMENDS_INTERVENTION]->(sdec)
        MERGE (opel2)-[:RECOMMENDS_INTERVENTION]->(utc)
        """,
        """
        MATCH (opel3:OPEL {level: 3}), (sdec:Intervention {name: 'SDEC'}), (vw:Intervention {name: 'Virtual_Ward'}), (amb:Intervention {name: 'Ambulance_Handover_45Min'})
        MERGE (opel3)-[:MANDATES_INTERVENTION]->(sdec)
        MERGE (opel3)-[:MANDATES_INTERVENTION]->(vw)
        MERGE (opel3)-[:MANDATES_INTERVENTION]->(amb)
        """,
        """
        MATCH (opel4:OPEL {level: 4}), (sdec:Intervention {name: 'SDEC'}), (vw:Intervention {name: 'Virtual_Ward'}), (spoa:Intervention {name: 'SPoA'}), (amb:Intervention {name: 'Ambulance_Handover_45Min'})
        MERGE (opel4)-[:MANDATES_INTERVENTION]->(sdec)
        MERGE (opel4)-[:MANDATES_INTERVENTION]->(vw)
        MERGE (opel4)-[:MANDATES_INTERVENTION]->(spoa)
        MERGE (opel4)-[:MANDATES_INTERVENTION]->(amb)
        """,
        # 6. Connect Cold Health Alert Levels to interventions
        """
        MATCH (c_amber:AlertLevel {code: 'Amber'}), (opel3:OPEL {level: 3}), (vw:Intervention {name: 'Virtual_Ward'}), (sdec:Intervention {name: 'SDEC'})
        MERGE (c_amber)-[:ESCALATES_TO]->(opel3)
        MERGE (c_amber)-[:RECOMMENDS_INTERVENTION]->(vw)
        MERGE (c_amber)-[:RECOMMENDS_INTERVENTION]->(sdec)
        """,
        """
        MATCH (c_red:AlertLevel {code: 'Red'}), (opel4:OPEL {level: 4}), (vw:Intervention {name: 'Virtual_Ward'}), (spoa:Intervention {name: 'SPoA'}), (amb:Intervention {name: 'Ambulance_Handover_45Min'})
        MERGE (c_red)-[:ESCALATES_TO]->(opel4)
        MERGE (c_red)-[:MANDATES_INTERVENTION]->(vw)
        MERGE (c_red)-[:MANDATES_INTERVENTION]->(spoa)
        MERGE (c_red)-[:MANDATES_INTERVENTION]->(amb)
        """,
    ]

    for stmt in statements:
        client.run_query(stmt)

    logger.info("ontology_nodes_and_relationships_seeded")
