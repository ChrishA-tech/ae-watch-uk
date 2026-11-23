"""Neo4j Community Graph Database Client for AE-Watch UK.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

from typing import Any

from neo4j import Driver, GraphDatabase
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ae_watch.config import settings


class Neo4jGraphClient:
    """Manages connection pool, session execution, and schema constraints on Neo4j."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        self._driver: Driver | None = None

    def get_driver(self) -> Driver:
        """Lazily initialize and return the Neo4j driver instance."""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=30 * 60,
                max_connection_pool_size=50,
            )
        return self._driver

    def close(self) -> None:
        """Close driver connection pool cleanly."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def run_query(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query with parameters and return records as dictionaries."""
        driver = self.get_driver()
        with driver.session() as session:
            result = session.run(query.strip(), parameters or {})
            return [record.data() for record in result]

    def execute_write(self, cypher_action, *args: Any, **kwargs: Any) -> Any:
        """Execute transactional write function."""
        driver = self.get_driver()
        with driver.session() as session:
            return session.execute_write(cypher_action, *args, **kwargs)


graph_client = Neo4jGraphClient()
