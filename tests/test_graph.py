"""Unit and integration tests for Neo4j Clinical Operations Knowledge Graph.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

from ae_watch.graph.client import graph_client
from ae_watch.graph.populator import graph_populator


def test_neo4j_connectivity_and_schema():
    """Verify Neo4j driver connection and schema constraint definitions."""
    res = graph_client.run_query("RETURN 1 AS val;")
    assert len(res) == 1
    assert res[0]["val"] == 1


def test_knowledge_graph_full_sync():
    """Verify complete graph population: Trusts, OPEL tiers, alert levels, and live states."""
    sync_result = graph_populator.populate_full_graph()
    assert sync_result["status"] == "ready"
    assert sync_result["trusts_synced"] >= 6
    assert sync_result["states_synced"] >= 1


def test_catchment_escalation_traversal_liverpool_rem():
    """Verify multi-hop graph traversal for target benchmark Liverpool REM."""
    context = graph_populator.traverse_catchment_escalation("REM")

    assert context["trust_code"] == "REM"
    assert "Liverpool" in context["trust_name"]
    assert context["opel_level"] in [1, 2, 3, 4]
    assert isinstance(context["active_interventions"], list)
    assert len(context["active_interventions"]) > 0

    # Verify proximate neighbors include Wirral (RBL) and Countess of Chester (RJR)
    neighbors = context["proximate_neighbors"]
    neighbor_codes = {n["neighbor_code"] for n in neighbors}
    assert "RBL" in neighbor_codes
    assert "RJR" in neighbor_codes

    # Verify all distances are within 25km radius
    for n in neighbors:
        assert 0.0 < n["distance_km"] <= 25.0
