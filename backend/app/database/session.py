"""
ARGUS Platform — Database Session Factory
SQLite + SQLAlchemy async-compatible session management.
"""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database.models import Base


# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite
    echo=settings.DEBUG,
)


# Enable WAL mode for better SQLite concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def init_db() -> None:
    """Create all tables and seed initial knowledge base data."""
    Base.metadata.create_all(bind=engine)
    _seed_knowledge_base()
    _seed_users()


def _seed_users() -> None:
    """Seed a default admin user."""
    from app.database.models import User, UserRole
    from app.core.security import hash_password

    with get_db() as db:
        if db.query(User).count() > 0:
            return

        user = User(
            email="admin@argus.defense",
            username="admin@argus.defense",
            hashed_password=hash_password("password123"),
            full_name="Chief Commander",
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(user)
        db.commit()


def _seed_knowledge_base() -> None:
    """Seed historical incident data for the KnowledgeAgent."""
    from app.database.models import KnowledgeBase, IncidentType, RiskLevel

    with get_db() as db:
        # Check if already seeded
        if db.query(KnowledgeBase).count() > 0:
            return

        historical_incidents = [
            KnowledgeBase(
                incident_type=IncidentType.BRIDGE_FAILURE,
                title="I-35W Mississippi River Bridge Collapse",
                description="The I-35W bridge in Minneapolis collapsed during rush hour. Fatigue cracks in gusset plates were the primary cause. 13 people died, 145 were injured.",
                location="Minneapolis, Minnesota, USA",
                year=2007,
                risk_level=RiskLevel.CRITICAL,
                outcome="Complete structural collapse during peak traffic. Bridge fell into Mississippi River.",
                lessons_learned="Regular ultrasonic testing of gusset plates mandatory. Visual inspection insufficient for internal fatigue cracks. Load limits must be enforced.",
                casualties=13,
                economic_damage_usd=234_000_000,
                keywords=["gusset plate", "fatigue crack", "steel bridge", "collapse", "rush hour", "structural failure"],
            ),
            KnowledgeBase(
                incident_type=IncidentType.BRIDGE_FAILURE,
                title="Fern Hollow Bridge Collapse — Pittsburgh",
                description="A 50-year-old bridge in Pittsburgh collapsed on January 28, 2022 due to decades of deferred maintenance and severe deterioration.",
                location="Pittsburgh, Pennsylvania, USA",
                year=2022,
                risk_level=RiskLevel.HIGH,
                outcome="Partial collapse. No fatalities but several injuries. Vehicles fell into ravine.",
                lessons_learned="Bridges rated 'poor' condition must be immediately load-restricted. Deferred maintenance creates exponential risk.",
                casualties=0,
                economic_damage_usd=25_000_000,
                keywords=["deterioration", "maintenance", "concrete", "aging infrastructure", "partial collapse"],
            ),
            KnowledgeBase(
                incident_type=IncidentType.URBAN_FLOOD,
                title="Houston Hurricane Harvey Flooding",
                description="Hurricane Harvey caused catastrophic flooding in Houston metropolitan area. Over 60 inches of rain fell in some areas over 4 days. 88 deaths, $125B in damages.",
                location="Houston, Texas, USA",
                year=2017,
                risk_level=RiskLevel.CRITICAL,
                outcome="33,000+ rescued. 300,000 structures damaged. Major infrastructure disruption for months.",
                lessons_learned="Urban sprawl eliminated natural flood absorption. Reservoir capacity was insufficient. Early evacuation orders save lives.",
                casualties=88,
                economic_damage_usd=125_000_000_000,
                keywords=["flood", "hurricane", "rainfall", "urban", "drainage", "reservoir", "evacuation"],
            ),
            KnowledgeBase(
                incident_type=IncidentType.URBAN_FLOOD,
                title="Pakistan Super Floods",
                description="One third of Pakistan submerged in 2022 floods. Record monsoon rainfall combined with glacial melt caused unprecedented disaster.",
                location="Pakistan",
                year=2022,
                risk_level=RiskLevel.CRITICAL,
                outcome="1,700+ deaths. 33 million affected. $30B in economic losses.",
                lessons_learned="Climate change amplifies flood severity. Early warning systems and pre-positioned supplies critical.",
                casualties=1739,
                economic_damage_usd=30_000_000_000,
                keywords=["monsoon", "glacial melt", "infrastructure damage", "displacement", "early warning"],
            ),
            KnowledgeBase(
                incident_type=IncidentType.WILDFIRE,
                title="Camp Fire — Paradise, California",
                description="Deadliest wildfire in California history. Destroyed town of Paradise. Caused by PG&E power line failure.",
                location="Butte County, California, USA",
                year=2018,
                risk_level=RiskLevel.CRITICAL,
                outcome="85 deaths. 18,804 structures destroyed. 153,336 acres burned.",
                lessons_learned="Power infrastructure in fire zones must be hardened. Evacuation plans must account for elderly and disabled populations.",
                casualties=85,
                economic_damage_usd=16_500_000_000,
                keywords=["wildfire", "power line", "evacuation", "utility", "dry conditions", "wind", "structure loss"],
            ),
            KnowledgeBase(
                incident_type=IncidentType.WILDFIRE,
                title="Maui Lahaina Wildfire",
                description="Rapidly spreading wildfire destroyed historic town of Lahaina in August 2023. Fueled by high winds from Hurricane Dora and dry conditions.",
                location="Lahaina, Maui, Hawaii, USA",
                year=2023,
                risk_level=RiskLevel.CRITICAL,
                outcome="100+ deaths. 2,200+ structures destroyed. Historic downtown completely lost.",
                lessons_learned="Utility power lines should have been de-energized during extreme wind events. Warning systems failed to alert residents.",
                casualties=100,
                economic_damage_usd=5_500_000_000,
                keywords=["wildfire", "wind", "utility failure", "warning system", "coastal fire", "rapid spread"],
            ),
            KnowledgeBase(
                incident_type=IncidentType.POWER_GRID_FAILURE,
                title="Texas Winter Storm Uri Power Grid Failure",
                description="Unprecedented winter storm caused massive power generation failures across Texas. 246 Texans died. Millions without power for days in freezing temperatures.",
                location="Texas, USA",
                year=2021,
                risk_level=RiskLevel.CRITICAL,
                outcome="246 deaths. $195B economic damage. 4.5 million homes without power.",
                lessons_learned="Grid winterization mandatory in extreme weather states. Market design created perverse incentives against reliability investment.",
                casualties=246,
                economic_damage_usd=195_000_000_000,
                keywords=["power grid", "winter storm", "freezing", "grid failure", "natural gas", "thermal plants", "ERCOT"],
            ),
            KnowledgeBase(
                incident_type=IncidentType.POWER_GRID_FAILURE,
                title="Northeast Blackout 2003",
                description="Cascading power failure affected 55 million people in US and Canada. Started with software bug and overgrown trees contacting power lines.",
                location="Northeast USA and Ontario, Canada",
                year=2003,
                risk_level=RiskLevel.HIGH,
                outcome="55 million without power. 11 deaths. $6B economic damage.",
                lessons_learned="Grid monitoring software must have failsafes. Tree trimming compliance critical. Cascade prevention protocols essential.",
                casualties=11,
                economic_damage_usd=6_000_000_000,
                keywords=["blackout", "cascade failure", "software bug", "transmission line", "grid stability"],
            ),
        ]

        db.add_all(historical_incidents)
        db.commit()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Synchronous database session context manager."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
