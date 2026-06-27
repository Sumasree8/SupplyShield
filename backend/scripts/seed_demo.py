#!/usr/bin/env python3
"""
SupplyShield AI — Development Seed Script

Creates a realistic automotive supply chain for demonstration purposes.

Usage:
    python scripts/seed_demo.py

Requires DATABASE_URL and SECRET_KEY in environment (or .env file).
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()



async def seed():
    # Late import so settings can load from .env
    from src.config.settings import get_settings
    from src.config.database import AsyncSessionLocal, Base, engine
    from src.models.core import Organization, User
    from src.models.supply_chain import Supplier, Material, SupplierMaterial, SupplyRelationship
    from src.models.risk import Alert, AlertSeverity, AlertStatus, RiskCategory, RiskEvent
    from src.services.auth_service import hash_password
    from src.services.risk_scoring_service import RiskScoringEngine

    # Safety: never let the demo seeder (which RESETS all tables) run in prod.
    if get_settings().ENVIRONMENT == "production":
        print("Refusing to run the demo seeder with ENVIRONMENT=production.")
        sys.exit(1)

    print("SupplyShield AI — Demo Seed Script")
    print("Seeding a realistic demo supply chain...\n")

    # Reset to a clean slate so the seeder is safely re-runnable.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:

        # ── Organization ──────────────────────────────────────────────────
        org = Organization(
            name="Apex Automotive Group",
            industry="Automotive",
            country="United States",
        )
        db.add(org)
        await db.flush()
        print(f"✓ Organization: {org.name} ({org.id})")

        # ── Users ─────────────────────────────────────────────────────────
        # The first entry is the headline "quick demo" login.
        users_data = [
            ("demo@gmail.com", "Demo User", "admin", "demo@1234"),
            ("admin@demo.supplychield.ai", "Demo Admin", "admin", "DemoPassword123!"),
            ("analyst@demo.supplychield.ai", "Sarah Chen", "risk_analyst", "DemoPassword123!"),
            ("procurement@demo.supplychield.ai", "James Wilson", "procurement_manager", "DemoPassword123!"),
            ("executive@demo.supplychield.ai", "Maria Rodriguez", "executive_viewer", "DemoPassword123!"),
        ]
        for email, name, role, pwd in users_data:
            u = User(
                organization_id=org.id,
                email=email,
                hashed_password=hash_password(pwd),
                full_name=name,
                role=role,
            )
            db.add(u)
        await db.flush()
        print(f"✓ Created {len(users_data)} demo users")

        # ── Tier 1 Suppliers (direct) ─────────────────────────────────────
        tier1 = []
        t1_data = [
            ("Denso Corporation", "Japan", "Kariya", "Electronics Manufacturing", 168529, 47800),
            ("Bosch Automotive", "Germany", "Stuttgart", "Automotive", 402600, 78700),
            ("Magna International", "Canada", "Aurora", "Automotive", 158000, 39400),
            ("Continental AG", "Germany", "Hanover", "Automotive", 200000, 44400),
        ]
        for name, country, city, industry, employees, revenue_m in t1_data:
            s = Supplier(
                organization_id=org.id,
                name=name,
                country=country, city=city,
                tier=1, status="active",
                industry=industry,
                employee_count=employees,
                annual_revenue_usd=revenue_m * 1_000_000,
                certifications={"IATF16949": "2026-12-31", "ISO14001": "2025-06-30"},
            )
            db.add(s)
            tier1.append(s)
        await db.flush()
        print(f"✓ Created {len(tier1)} Tier 1 suppliers")

        # ── Tier 2 Suppliers ──────────────────────────────────────────────
        tier2 = []
        t2_data = [
            ("Taiwan Semiconductor Mfg", "Taiwan", "Hsinchu", "Semiconductors", 73090, 69000),
            ("Samsung SDI", "South Korea", "Seoul", "Electronics Manufacturing", 23000, 8900),
            ("Nippon Steel", "Japan", "Tokyo", "Metals & Mining", 106000, 17800),
            ("BASF SE", "Germany", "Ludwigshafen", "Chemicals", 111000, 78600),
            ("Aptiv PLC", "Ireland", "Dublin", "Electronics Manufacturing", 196000, 16900),
            ("TE Connectivity", "Switzerland", "Schaffhausen", "Electronics Manufacturing", 89000, 15600),
        ]
        for name, country, city, industry, employees, revenue_m in t2_data:
            s = Supplier(
                organization_id=org.id,
                name=name,
                country=country, city=city,
                tier=2, status="active",
                industry=industry,
                employee_count=employees,
                annual_revenue_usd=revenue_m * 1_000_000,
                certifications={"ISO9001": "2025-12-31"},
            )
            db.add(s)
            tier2.append(s)
        await db.flush()
        print(f"✓ Created {len(tier2)} Tier 2 suppliers")

        # ── Tier 3 Suppliers ──────────────────────────────────────────────
        tier3 = []
        t3_data = [
            ("Yanzhou Coal Mining", "China", "Shandong", "Energy", 88000, 12000),
            ("Freeport-McMoRan", "United States", "Phoenix", "Metals & Mining", 27000, 5900),
            ("Albemarle Corporation", "United States", "Charlotte", "Chemicals", 7100, 9600),
            ("Umicore", "Belgium", "Brussels", "Metals & Mining", 11000, 3400),
        ]
        for name, country, city, industry, employees, revenue_m in t3_data:
            s = Supplier(
                organization_id=org.id,
                name=name,
                country=country, city=city,
                tier=3, status="active",
                industry=industry,
                employee_count=employees,
                annual_revenue_usd=revenue_m * 1_000_000,
            )
            db.add(s)
            tier3.append(s)
        # Demo variety: flag one upstream supplier as suspended so the risk
        # scores span more than one level (operational risk pushes it higher).
        tier3[0].status = "suspended"
        await db.flush()
        print(f"✓ Created {len(tier3)} Tier 3 suppliers")

        # ── Materials ─────────────────────────────────────────────────────
        materials_data = [
            ("Automotive-Grade Microcontrollers", "Semiconductors", "8473.30", "high"),
            ("Lithium Carbonate", "Battery Materials", "2825.20", "critical"),
            ("Advanced High-Strength Steel", "Metals", "7209.16", "high"),
            ("Automotive Wiring Harnesses", "Electrical Systems", "8544.30", "medium"),
            ("Polypropylene Compounds", "Plastics", "3902.10", "medium"),
            ("Copper Wire Rod", "Metals", "7408.11", "high"),
        ]
        materials = []
        for name, category, hs_code, criticality in materials_data:
            m = Material(
                organization_id=org.id,
                name=name,
                category=category,
                hs_code=hs_code,
                criticality=criticality,
                unit_of_measure="units",
            )
            db.add(m)
            materials.append(m)
        await db.flush()
        print(f"✓ Created {len(materials)} materials")

        # ── Supply Relationships (graph edges) ────────────────────────────
        # T3 → T2
        rel_pairs = [
            (tier3[0], tier2[2]),   # Coal → Nippon Steel
            (tier3[1], tier2[2]),   # Freeport copper → Nippon Steel
            (tier3[2], tier2[1]),   # Albemarle lithium → Samsung SDI (sole source)
            (tier3[3], tier2[1]),   # Umicore → Samsung SDI
            # T2 → T1
            (tier2[0], tier1[0]),   # TSMC → Denso
            (tier2[0], tier1[3]),   # TSMC → Continental
            (tier2[1], tier1[0]),   # Samsung SDI → Denso
            (tier2[2], tier1[1]),   # Nippon Steel → Bosch
            (tier2[2], tier1[2]),   # Nippon Steel → Magna
            (tier2[3], tier1[1]),   # BASF → Bosch
            (tier2[4], tier1[3]),   # Aptiv → Continental
            (tier2[5], tier1[0]),   # TE Connectivity → Denso
        ]
        for from_s, to_s in rel_pairs:
            rel = SupplyRelationship(
                organization_id=org.id,
                from_supplier_id=from_s.id,
                to_supplier_id=to_s.id,
                relationship_type="SUPPLIES_TO",
                annual_volume_usd=float(
                    (from_s.annual_revenue_usd or 1_000_000) * 0.12
                ),
                lead_time_days=30,
            )
            db.add(rel)

        # Mark the lithium → Samsung SDI as sole source
        sm = SupplierMaterial(
            supplier_id=tier3[2].id,
            material_id=materials[1].id,
            is_sole_source=True,
            lead_time_days=90,
            annual_spend_usd=850_000_000,
        )
        db.add(sm)

        await db.flush()
        rel_count = len(rel_pairs)
        print(f"✓ Created {rel_count} supply relationships")
        print("✓ Marked lithium supplier as sole-source dependency (critical risk)")

        # ── Demo external risk events ─────────────────────────────────────
        # Sample events matched to supplier geographies. These drive the
        # climate/geopolitical/logistics components of the risk scores below
        # and populate the "External Risk Events" view. (In production these
        # come from the NOAA/GDELT/OpenWeather ingestion jobs.)
        events = [
            RiskEvent(
                source="noaa", category=RiskCategory.CLIMATE,
                title="Typhoon warning — East Asia coastal manufacturing belt",
                description="Category 4 typhoon tracking toward Taiwan and southern Japan.",
                severity="severe", affected_countries=["Taiwan", "Japan"],
                event_date=datetime.now(timezone.utc),
            ),
            RiskEvent(
                source="gdelt", category=RiskCategory.GEOPOLITICAL,
                title="Export controls tighten on critical minerals",
                description="New restrictions announced affecting battery-material exports.",
                severity="extreme", affected_countries=["China"],
                event_date=datetime.now(timezone.utc),
            ),
            RiskEvent(
                source="gdelt", category=RiskCategory.GEOPOLITICAL,
                title="Semiconductor trade tensions escalate",
                description="Heightened cross-strait tension raising semiconductor supply concerns.",
                severity="severe", affected_countries=["Taiwan"],
                event_date=datetime.now(timezone.utc),
            ),
            RiskEvent(
                source="port_congestion_api", category=RiskCategory.LOGISTICS,
                title="Port congestion — Northern Europe",
                description="Multi-day backlogs at major German seaports.",
                severity="moderate", affected_countries=["Germany"],
                event_date=datetime.now(timezone.utc),
            ),
        ]
        db.add_all(events)
        await db.flush()
        print(f"✓ Ingested {len(events)} demo risk events")

        # ── Computed risk scores ──────────────────────────────────────────
        # Real, explainable scores derived from the seeded data (sole-source
        # flags, downstream concentration, missing certs) AND the demo events
        # above — so the Risk page shows meaningful variety on first login.
        engine_svc = RiskScoringEngine(db)
        all_suppliers = tier1 + tier2 + tier3
        for s in all_suppliers:
            result = await engine_svc.calculate_supplier_risk(s, str(org.id))
            await engine_svc.persist_score(result, str(org.id))
        print(f"✓ Calculated explainable risk scores for {len(all_suppliers)} suppliers")

        # ── Demo alerts ───────────────────────────────────────────────────
        alerts = [
            Alert(
                organization_id=org.id,
                supplier_id=tier3[2].id,
                title="Sole-source dependency: Lithium Carbonate",
                description=(
                    "Albemarle is the only qualified source for lithium carbonate feeding "
                    "Samsung SDI. A disruption here has no upstream alternative."
                ),
                category=RiskCategory.DEPENDENCY,
                severity=AlertSeverity.CRITICAL,
                status=AlertStatus.CREATED,
                trigger_type="manual",
                notifications_sent=[],
            ),
            Alert(
                organization_id=org.id,
                supplier_id=tier2[0].id,
                title="Concentration risk: TSMC (Taiwan)",
                description=(
                    "TSMC supplies multiple Tier-1 suppliers from a single geography. "
                    "Review geographic diversification."
                ),
                category=RiskCategory.GEOPOLITICAL,
                severity=AlertSeverity.HIGH,
                status=AlertStatus.CREATED,
                trigger_type="manual",
                notifications_sent=[],
            ),
        ]
        db.add_all(alerts)

        await db.commit()
        print(f"✓ Created {len(alerts)} demo alerts")

    print()
    print("=" * 60)
    print("Demo seed complete!")
    print()
    print("▶ Quick demo login:")
    print("     demo@gmail.com / demo@1234   (admin — sees everything)")
    print()
    print("  Other role-based logins (password: DemoPassword123!):")
    print("     admin@demo.supplychield.ai        — Admin")
    print("     analyst@demo.supplychield.ai      — Risk Analyst")
    print("     procurement@demo.supplychield.ai  — Procurement Manager")
    print("     executive@demo.supplychield.ai    — Executive Viewer (read-only)")
    print()
    print("NOTE: This is demo data, intended for development only.")
    print("Do not use these credentials in a production environment.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed())
