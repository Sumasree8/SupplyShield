"""
Supply chain graph service.
Builds and traverses the supplier dependency graph.
Supports Neo4j (primary) and NetworkX (fallback/analytics).
"""
import asyncio
from typing import Dict, Any
from collections import defaultdict

import structlog
import networkx as nx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.graph_db import get_graph_driver
from src.models.supply_chain import Supplier, SupplyRelationship, Facility

log = structlog.get_logger()


class GraphService:
    """
    Supply chain graph operations.
    All traversal logic is deterministic and based on stored relationships.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._neo4j = get_graph_driver()

    async def build_networkx_graph(self, organization_id: str) -> nx.DiGraph:
        """
        Build a directed graph from PostgreSQL data.
        Used when Neo4j is unavailable or for analytical operations.
        """
        G = nx.DiGraph()

        # Load suppliers as nodes
        result = await self.db.execute(
            select(Supplier).where(
                Supplier.organization_id == organization_id,
                Supplier.is_active == True
            )
        )
        suppliers = result.scalars().all()

        for s in suppliers:
            G.add_node(
                str(s.id),
                name=s.name,
                country=s.country,
                tier=s.tier,
                status=s.status.value,
                industry=s.industry or "",
                latitude=s.latitude,
                longitude=s.longitude,
            )

        # Load relationships as edges
        result = await self.db.execute(
            select(SupplyRelationship).where(
                SupplyRelationship.organization_id == organization_id,
                SupplyRelationship.is_active == True
            )
        )
        relationships = result.scalars().all()

        for r in relationships:
            G.add_edge(
                str(r.from_supplier_id),
                str(r.to_supplier_id),
                relationship_type=r.relationship_type.value,
                annual_volume_usd=r.annual_volume_usd,
                lead_time_days=r.lead_time_days,
            )

        return G

    async def get_graph_data_for_visualization(self, organization_id: str) -> Dict[str, Any]:
        """
        Return nodes + edges in D3/Cytoscape-compatible format.
        """
        G = await self.build_networkx_graph(organization_id)

        nodes = []
        for node_id, data in G.nodes(data=True):
            nodes.append({
                "id": node_id,
                "label": data.get("name", node_id),
                "tier": data.get("tier", 0),
                "country": data.get("country", ""),
                "status": data.get("status", "active"),
                "industry": data.get("industry", ""),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
            })

        edges = []
        for from_id, to_id, data in G.edges(data=True):
            edges.append({
                "id": f"{from_id}->{to_id}",
                "source": from_id,
                "target": to_id,
                "type": data.get("relationship_type", "SUPPLIES_TO"),
                "annual_volume_usd": data.get("annual_volume_usd"),
                "lead_time_days": data.get("lead_time_days"),
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": G.number_of_nodes(),
                "total_edges": G.number_of_edges(),
                "tier_breakdown": self._tier_breakdown(G),
                "country_breakdown": self._country_breakdown(G),
            }
        }

    async def get_upstream_dependencies(
        self, organization_id: str, supplier_id: str, max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Find all upstream suppliers (who supplies to this supplier).
        Returns the dependency chain up to max_depth tiers.
        """
        G = await self.build_networkx_graph(organization_id)

        if supplier_id not in G:
            return {"supplier_id": supplier_id, "dependencies": [], "depth": 0}

        # Reverse graph: traverse who feeds into this supplier
        G_rev = G.reverse()

        try:
            paths = {}
            for node in nx.descendants(G_rev, supplier_id):
                try:
                    path = nx.shortest_path(G_rev, supplier_id, node)
                    if len(path) - 1 <= max_depth:
                        paths[node] = path
                except nx.NetworkXNoPath:
                    pass

            dependencies = []
            for node_id, path in paths.items():
                node_data = G.nodes.get(node_id, {})
                dependencies.append({
                    "supplier_id": node_id,
                    "name": node_data.get("name", ""),
                    "tier": node_data.get("tier", 0),
                    "country": node_data.get("country", ""),
                    "depth": len(path) - 1,
                    "path": path,
                })

            return {
                "supplier_id": supplier_id,
                "dependencies": sorted(dependencies, key=lambda x: x["depth"]),
                "total_dependencies": len(dependencies),
            }
        except Exception as e:
            log.error("graph.upstream_dependencies_failed", error=str(e), supplier_id=supplier_id)
            raise

    async def simulate_disruption_impact(
        self, organization_id: str, affected_supplier_id: str
    ) -> Dict[str, Any]:
        """
        Simulate ripple effect: if this supplier is disrupted,
        which downstream suppliers/products are impacted?

        Returns cascading impact by tier.
        """
        G = await self.build_networkx_graph(organization_id)

        if affected_supplier_id not in G:
            return {"error": "Supplier not found in graph"}

        # Find all nodes reachable downstream from the affected supplier
        downstream = nx.descendants(G, affected_supplier_id)

        impact_by_tier = defaultdict(list)
        for node_id in downstream:
            node_data = G.nodes.get(node_id, {})
            tier = node_data.get("tier", 0)
            try:
                path = nx.shortest_path(G, affected_supplier_id, node_id)
                impact_by_tier[tier].append({
                    "supplier_id": node_id,
                    "name": node_data.get("name", ""),
                    "country": node_data.get("country", ""),
                    "distance_from_disruption": len(path) - 1,
                    "propagation_path": path,
                })
            except nx.NetworkXNoPath:
                pass

        # Calculate criticality: suppliers with no alternative upstream
        sole_source_impacts = []
        for node_id in downstream:
            predecessors = list(G.predecessors(node_id))
            if len(predecessors) == 1 and predecessors[0] == affected_supplier_id:
                node_data = G.nodes.get(node_id, {})
                sole_source_impacts.append({
                    "supplier_id": node_id,
                    "name": node_data.get("name", ""),
                    "reason": "Single-source dependency — no alternative upstream supplier",
                })

        return {
            "disrupted_supplier_id": affected_supplier_id,
            "total_affected": len(downstream),
            "impact_by_tier": dict(impact_by_tier),
            "sole_source_vulnerabilities": sole_source_impacts,
            "disruption_radius": max((len(nx.shortest_path(G, affected_supplier_id, n)) - 1 for n in downstream), default=0),
        }

    async def get_tier_summary(self, organization_id: str) -> Dict[str, Any]:
        """Summary statistics by tier."""
        G = await self.build_networkx_graph(organization_id)
        return {
            "tier_breakdown": self._tier_breakdown(G),
            "total_suppliers": G.number_of_nodes(),
            "total_relationships": G.number_of_edges(),
        }

    def _tier_breakdown(self, G: nx.DiGraph) -> Dict[int, int]:
        counts = defaultdict(int)
        for _, data in G.nodes(data=True):
            counts[data.get("tier", 0)] += 1
        return dict(counts)

    def _country_breakdown(self, G: nx.DiGraph) -> Dict[str, int]:
        counts = defaultdict(int)
        for _, data in G.nodes(data=True):
            counts[data.get("country", "Unknown")] += 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    async def upsert_supplier_in_neo4j(self, supplier: Supplier):
        """Sync supplier node to Neo4j if available.

        The Neo4j Python driver is synchronous; running its blocking I/O
        directly in this async handler would stall the event loop, so we
        offload it to a worker thread.
        """
        if not self._neo4j:
            return
        params = dict(
            id=str(supplier.id),
            name=supplier.name,
            country=supplier.country,
            tier=supplier.tier,
            status=supplier.status.value,
            industry=supplier.industry or "",
        )
        await asyncio.to_thread(self._upsert_supplier_sync, params)

    def _upsert_supplier_sync(self, params: dict) -> None:
        with self._neo4j.session() as session:
            session.run(
                """
                MERGE (s:Supplier {id: $id})
                SET s.name = $name,
                    s.country = $country,
                    s.tier = $tier,
                    s.status = $status,
                    s.industry = $industry
                """,
                **params,
            )

    async def upsert_relationship_in_neo4j(self, rel: SupplyRelationship):
        """Sync supply relationship to Neo4j if available (offloaded to a thread)."""
        if not self._neo4j:
            return
        params = dict(
            from_id=str(rel.from_supplier_id),
            to_id=str(rel.to_supplier_id),
            volume=rel.annual_volume_usd,
            lead_time=rel.lead_time_days,
        )
        await asyncio.to_thread(self._upsert_relationship_sync, params)

    def _upsert_relationship_sync(self, params: dict) -> None:
        with self._neo4j.session() as session:
            session.run(
                """
                MATCH (a:Supplier {id: $from_id})
                MATCH (b:Supplier {id: $to_id})
                MERGE (a)-[r:SUPPLIES_TO]->(b)
                SET r.annual_volume_usd = $volume,
                    r.lead_time_days = $lead_time
                """,
                **params,
            )
