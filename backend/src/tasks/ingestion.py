"""
Background ingestion tasks — Phase 2.
Scheduled jobs that ingest external risk signals from NOAA, GDELT, OpenWeather.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional
import structlog

try:
    from celery import Celery
    from celery.schedules import crontab
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

import httpx

from src.config.settings import get_settings

log = structlog.get_logger()
settings = get_settings()

if CELERY_AVAILABLE:
    celery_app = Celery(
        "supplychield",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
    )

    celery_app.conf.beat_schedule = {
        "ingest-noaa-alerts-hourly": {
            "task": "src.tasks.ingestion.ingest_noaa_alerts",
            "schedule": crontab(minute=0),  # Every hour
        },
        "ingest-gdelt-events-every-4h": {
            "task": "src.tasks.ingestion.ingest_gdelt_events",
            "schedule": crontab(minute=0, hour="*/4"),
        },
        "ingest-openweather-every-6h": {
            "task": "src.tasks.ingestion.ingest_openweather",
            "schedule": crontab(minute=0, hour="*/6"),
        },
    }


async def _ingest_noaa_alerts():
    """
    Ingest NOAA weather alerts.
    https://www.weather.gov/documentation/services-web-api
    Requires: NOAA_API_KEY in environment
    """
    if not settings.NOAA_API_KEY:
        log.info("noaa.skipped", reason="NOAA_API_KEY not configured")
        return {"status": "skipped", "reason": "API key not configured"}

    url = "https://api.weather.gov/alerts/active"
    headers = {
        "User-Agent": "SupplyShieldAI/1.0 (supply-chain-risk@example.com)",
        "Accept": "application/geo+json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            events_ingested = 0
            from src.config.database import AsyncSessionLocal
            from src.models.risk import RiskEvent, RiskCategory

            async with AsyncSessionLocal() as db:
                for feature in data.get("features", [])[:50]:  # Process up to 50
                    props = feature.get("properties", {})
                    severity_map = {
                        "Extreme": "extreme", "Severe": "severe",
                        "Moderate": "moderate", "Minor": "minor",
                    }

                    event = RiskEvent(
                        source="noaa",
                        source_event_id=props.get("id"),
                        category=RiskCategory.CLIMATE,
                        title=props.get("headline", props.get("event", "Unknown NOAA Alert")),
                        description=props.get("description"),
                        severity=severity_map.get(props.get("severity", "Minor"), "minor"),
                        affected_countries=["US"],  # NOAA is US-focused
                        affected_regions=[props.get("areaDesc", "")],
                        raw_data=props,
                        event_date=datetime.fromisoformat(props["effective"].replace("Z", "+00:00")) if props.get("effective") else None,
                    )
                    db.add(event)
                    events_ingested += 1

                await db.commit()

            log.info("noaa.ingested", count=events_ingested)
            return {"status": "success", "events_ingested": events_ingested}

        except httpx.HTTPError as e:
            log.error("noaa.fetch_failed", error=str(e))
            return {"status": "error", "error": str(e)}


async def _ingest_gdelt_events():
    """
    Ingest geopolitical events from GDELT Project.
    https://api.gdeltproject.org
    Free API — no key required.
    """
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": "supply chain disruption OR trade restriction OR sanctions",
        "mode": "artlist",
        "maxrecords": 25,
        "format": "json",
        "timespan": "1d",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            from src.config.database import AsyncSessionLocal
            from src.models.risk import RiskEvent, RiskCategory

            events_ingested = 0
            async with AsyncSessionLocal() as db:
                for article in data.get("articles", [])[:25]:
                    event = RiskEvent(
                        source="gdelt",
                        source_event_id=article.get("url", "")[:255],
                        category=RiskCategory.GEOPOLITICAL,
                        title=article.get("title", "Unknown GDELT Event"),
                        description=article.get("seendates", ""),
                        severity="moderate",
                        affected_countries=_extract_countries(article),
                        raw_data=article,
                        event_date=datetime.now(timezone.utc),
                    )
                    db.add(event)
                    events_ingested += 1

                await db.commit()

            log.info("gdelt.ingested", count=events_ingested)
            return {"status": "success", "events_ingested": events_ingested}

        except Exception as e:
            log.error("gdelt.fetch_failed", error=str(e))
            return {"status": "error", "error": str(e)}


def _extract_countries(article: dict) -> list:
    """Extract country names from a GDELT artlist article.

    GDELT's artlist mode returns a `sourcecountry` field (the country the
    article's source is based in) — not a `mentions` object. The previous
    implementation read `mentions`, which is never present in this response,
    so `affected_countries` was always empty and events never matched suppliers.
    """
    country = article.get("sourcecountry")
    return [country] if country else []


if CELERY_AVAILABLE:
    @celery_app.task(name="src.tasks.ingestion.ingest_noaa_alerts", bind=True, max_retries=3)
    def ingest_noaa_alerts(self):
        return asyncio.run(_ingest_noaa_alerts())

    @celery_app.task(name="src.tasks.ingestion.ingest_gdelt_events", bind=True, max_retries=3)
    def ingest_gdelt_events(self):
        return asyncio.run(_ingest_gdelt_events())

    @celery_app.task(name="src.tasks.ingestion.ingest_openweather", bind=True, max_retries=3)
    def ingest_openweather(self):
        if not settings.OPENWEATHER_API_KEY:
            return {"status": "skipped", "reason": "OPENWEATHER_API_KEY not configured"}
        # OpenWeather One Call API ingestion placeholder
        return {"status": "not_implemented"}
