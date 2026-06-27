"""
Graph database configuration.
Primary: Neo4j
Fallback: NetworkX + PostgreSQL (for environments without Neo4j)
"""
from typing import Optional
import structlog
from neo4j import GraphDatabase, Driver

from src.config.settings import get_settings

log = structlog.get_logger()
settings = get_settings()

_driver: Optional[Driver] = None


def get_graph_driver() -> Optional[Driver]:
    """Return Neo4j driver if configured, else None (NetworkX fallback)."""
    global _driver
    if _driver is None and settings.NEO4J_URI:
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
            database=settings.NEO4J_DATABASE,
        )
    return _driver


def close_graph_driver():
    global _driver
    if _driver:
        _driver.close()
        _driver = None


NEO4J_SCHEMA = """
// SupplyShield AI - Neo4j Graph Schema
// Node constraints and indexes

CREATE CONSTRAINT supplier_id IF NOT EXISTS
FOR (s:Supplier) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT material_id IF NOT EXISTS
FOR (m:Material) REQUIRE m.id IS UNIQUE;

CREATE CONSTRAINT facility_id IF NOT EXISTS
FOR (f:Facility) REQUIRE f.id IS UNIQUE;

CREATE CONSTRAINT product_id IF NOT EXISTS
FOR (p:Product) REQUIRE p.id IS UNIQUE;

// Indexes for common query patterns
CREATE INDEX supplier_name IF NOT EXISTS FOR (s:Supplier) ON (s.name);
CREATE INDEX supplier_country IF NOT EXISTS FOR (s:Supplier) ON (s.country);
CREATE INDEX supplier_tier IF NOT EXISTS FOR (s:Supplier) ON (s.tier);

// Relationship types:
// (Supplier)-[:SUPPLIES_TO]->(Supplier)        — direct supply relationship
// (Supplier)-[:DEPENDS_ON]->(Material)         — material dependency
// (Supplier)-[:OPERATES]->(Facility)           — facility ownership
// (Facility)-[:PRODUCES]->(Product)            — production relationship
// (Facility)-[:SHIPS_TO]->(Facility)           — logistics link
// (Material)-[:COMPONENT_OF]->(Product)        — BOM relationship
"""
