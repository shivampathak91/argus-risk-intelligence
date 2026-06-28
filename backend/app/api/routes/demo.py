"""
ARGUS Platform — Demo Mode Routes
Launch built-in scenarios with pre-bundled sample data.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.deps import AnalystUser, DBSession
from app.database.models import Incident, IncidentType, Upload, UploadType, Workflow, WorkflowStatus
from app.database.schemas import DemoLaunch, DemoScenario, WorkflowResponse


router = APIRouter(prefix="/demo", tags=["Demo Mode"])

# ── Built-in scenario definitions ─────────────────────────────────────────────
DEMO_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "bridge_structural_failure",
        "name": "Bridge Structural Failure",
        "description": (
            "A routine inspection report reveals significant structural deterioration "
            "in a 45-year-old reinforced concrete bridge. Cracks, spalling, and corrosion "
            "observed across multiple load-bearing elements."
        ),
        "incident_type": IncidentType.BRIDGE_FAILURE,
        "location_name": "Riverside Highway Bridge, Sector 7",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "sample_text": """
BRIDGE STRUCTURAL INSPECTION REPORT
Date: 2024-01-15
Inspector: James Harrington, PE
Bridge ID: RHB-2024-007
Location: Riverside Highway Bridge, Sector 7
Year Built: 1979
Span Length: 127 meters
Load Rating: HS-20

CRITICAL FINDINGS:
1. Main span deck: Multiple transverse cracks (width 3.2mm - 6.8mm) observed
   at mid-span and quarter points. Crack depth estimated at 60-80% of deck thickness.
2. Pier Column 3: Significant concrete spalling (0.8m x 1.2m area) exposing
   corroded primary reinforcement. Rebar section loss estimated 35%.
3. Bearing pads: Severe deterioration on 6 of 8 bearings. Elastomeric material
   degraded, potential for fixed-end uplift under dynamic loading.
4. Expansion joints: Joint seals failed at 4 locations. Water infiltration
   evident causing salt damage to substructure.
5. Abutment North: Settlement of approximately 45mm measured. Differential
   settlement creating stress concentration in approach slab.

STRUCTURAL ASSESSMENT:
Overall condition rating: POOR (NBI Rating: 3)
Remaining service life estimate: 2-5 years without intervention
Load posting recommended: Reduce to 30% of design load immediately

IMMEDIATE ACTIONS REQUIRED:
- Emergency load restriction enforcement
- Temporary shoring of Pier Column 3
- 24/7 structural monitoring installation
- Detailed engineering assessment within 30 days
""",
    },
    {
        "id": "urban_flood",
        "name": "Urban Flood Event",
        "description": (
            "Severe monsoon rainfall has triggered urban flooding across 12 districts. "
            "River levels are rising rapidly. Infrastructure damage reports incoming "
            "from multiple locations."
        ),
        "incident_type": IncidentType.URBAN_FLOOD,
        "location_name": "Metro District Flood Zone, Sectors 3-15",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "sample_text": """
FLOOD EMERGENCY SITUATION REPORT
Reporting Agency: Municipal Disaster Management Authority
Date/Time: 2024-07-22 14:30 IST
Report Classification: URGENT

METEOROLOGICAL DATA:
24-hour rainfall: 312mm (Record: 287mm set in 1994)
48-hour forecast: Additional 180-250mm expected
River Level - Mithi River: 4.2m (Danger level: 3.0m, Flood level: 3.5m)
River Level - Ulhas River: 5.8m (Danger level: 4.5m) - CRITICAL
Tide prediction: High tide at 18:45 IST will compound flood risk

AFFECTED AREAS:
Sector 3: 45% submerged, 12,000 residents affected
Sector 7: Roads flooded, depth 0.8-1.5m, traffic halted
Sector 11: Residential colony flooded, 3,200 residents evacuated
Sector 14: Hospital access road blocked (60cm water depth)
Sector 15: Sewage overflow contamination reported

INFRASTRUCTURE DAMAGE:
- 2 underpasses closed (Andheri and Sion)
- 8 low-lying bridges closed to traffic
- 3 electrical substations shut down preventively
- Suburban railway: 40% services suspended
- Airport: International operations delayed 3+ hours

CASUALTIES/INJURIES:
Confirmed deaths: 6 (wall collapse, drowning)
Injuries: 34 (transported to hospitals)
Missing: 3 (search operations ongoing)
Evacuated: 8,400 persons as of 14:00 IST

RELIEF OPERATIONS:
NDRF teams deployed: 12
SDRF teams: 8
Army: 2 columns on standby
Rescue boats operational: 67
Relief camps activated: 14 (capacity: 12,000)
""",
    },
    {
        "id": "wildfire",
        "name": "Wildfire Threat Assessment",
        "description": (
            "Multiple wildfire ignitions detected in a high-risk zone. "
            "Wind speeds at 45 km/h, humidity at 12%, temperature 42°C. "
            "Communities within 15km radius under evacuation advisory."
        ),
        "incident_type": IncidentType.WILDFIRE,
        "location_name": "Pinecrest Forest Reserve, Zone 4",
        "latitude": 37.3382,
        "longitude": -121.8863,
        "sample_text": """
WILDFIRE INCIDENT REPORT - URGENT
Incident Name: PINECREST FIRE
Reporting Unit: Regional Fire Operations Center
Date: 2024-08-19
Time: 11:45 PDT
Incident Commander: Chief Maria Delgado

FIRE STATUS:
Total Acres: 2,847 (as of 11:00 PDT, rapidly growing)
Containment: 0%
Rate of Spread: EXTREME - estimated 800 acres/hour under current conditions
Fire Behavior: Spotting observed 1.5 miles ahead of main fire front

WEATHER CONDITIONS (Observed 11:30 PDT):
Temperature: 42°C (107°F)
Relative Humidity: 12%
Wind Speed: 45 km/h, gusts to 72 km/h
Wind Direction: Northeast, highly erratic
Red Flag Conditions: YES (Active Red Flag Warning through 20:00 PDT)
FFMC Index: 92 (Extreme)
ISI: 24 (Extreme)
FWI: 38 (Extreme)

STRUCTURES THREATENED:
Zone A (0-5km): 847 structures - IMMEDIATE THREAT
Zone B (5-10km): 2,340 structures - HIGH THREAT
Zone C (10-15km): 5,120 structures - MODERATE THREAT
Total Population at Risk: Approximately 18,400 persons

EVACUATIONS:
Mandatory evacuation: Zones A and B (implemented 10:30 PDT)
Evacuation warning: Zone C
Roads closed: Highway 17, Pinecrest Road, Summit Drive
Evacuation centers: High School (capacity 800), Community Center (400)
Persons evacuated: 4,200 (estimated 60% compliance in Zone A)

RESOURCES:
Ground crews: 12 Type I crews, 8 Type II crews (total 520 personnel)
Air tankers: 6 single-engine, 2 VLAT (Very Large Air Tankers)
Helicopters: 8 (4 water drops, 4 personnel)
Dozers: 14 operational
Critical shortage: Water tenders (only 6 of 20 requested available)
""",
    },
    {
        "id": "power_grid_failure",
        "name": "Power Grid Failure",
        "description": (
            "Cascading failures in the regional power grid have caused widespread outages. "
            "Three substations offline, affecting 2.4 million customers. "
            "Critical infrastructure including hospitals on backup power."
        ),
        "incident_type": IncidentType.POWER_GRID_FAILURE,
        "location_name": "Northern Grid Region — Substations A, B, C",
        "latitude": 41.8781,
        "longitude": -87.6298,
        "sample_text": """
POWER GRID EMERGENCY INCIDENT REPORT
Utility: Northern Regional Electric Authority
Incident ID: NREA-2024-GRID-0847
Classification: Level 3 - Major Outage Event
Time of Initial Fault: 03:42 CST

INCIDENT SEQUENCE:
03:42 - Lightning strike causes flashover at Substation Alpha (345kV)
03:42 - Protection systems isolate Alpha substation automatically
03:43 - Load redistribution increases current on Transmission Line 7-B by 180%
03:44 - Thermal overload protection trips Line 7-B (132kV)
03:45 - Cascade: Beta Substation overloaded, trips offline
03:47 - Gamma Substation voltage instability detected
03:49 - Gamma Substation manually de-energized (operator decision)
03:52 - System frequency drops to 59.3Hz (nominal: 60Hz)
03:55 - Automatic load shedding activates (800MW shed)
04:00 - Grid stabilized at reduced capacity

OUTAGE STATISTICS (as of 06:00 CST):
Customers without power: 2,412,000
Estimated restoration time: 18-72 hours (varies by area)
Peak demand lost: 1,847 MW
Generation online: 68% of normal capacity

CRITICAL FACILITIES AFFECTED:
- 14 hospitals on emergency generators
- 3 water treatment plants (2 on generator, 1 partially offline)
- 8 wastewater pumping stations offline (overflow risk: 4-6 hours)
- 2 data centers switched to UPS/generator
- Chicago O'Hare: Reduced operations, terminal A on generator

EQUIPMENT DAMAGE:
- Substation Alpha: 2 power transformers damaged (replacement: 6-12 weeks)
- Transmission Line 7-B: 3 towers require inspection, 1 potential damage
- Beta Substation: Protective relay failure (replacement: 48 hours)

RESTORATION PRIORITY:
P1 (0-6 hours): Hospitals, water treatment, emergency services
P2 (6-18 hours): Major commercial, residential dense areas
P3 (18-72 hours): Remaining residential, rural areas
""",
    },
]


@router.get("/scenarios", response_model=List[DemoScenario])
def list_demo_scenarios() -> List[DemoScenario]:
    """Return the list of available built-in demo scenarios."""
    return [
        DemoScenario(
            id=s["id"],
            name=s["name"],
            description=s["description"],
            incident_type=s["incident_type"].value,
        )
        for s in DEMO_SCENARIOS
    ]


@router.post("/launch", response_model=WorkflowResponse, status_code=201)
def launch_demo(
    body: DemoLaunch,
    background_tasks: BackgroundTasks,
    db: DBSession,
    current_user: AnalystUser,
) -> Workflow:
    """
    Launch a demo scenario:
    1. Create a demo incident
    2. Write the bundled sample text to disk
    3. Register it as an upload
    4. Trigger the full agent pipeline
    """
    # Find the scenario
    scenario = next((s for s in DEMO_SCENARIOS if s["id"] == body.scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Demo scenario '{body.scenario_id}' not found")

    # Create incident
    incident = Incident(
        title=f"[DEMO] {scenario['name']}",
        description=scenario["description"],
        incident_type=scenario["incident_type"],
        location_name=scenario["location_name"],
        latitude=scenario["latitude"],
        longitude=scenario["longitude"],
        is_demo=True,
        created_by=current_user.id,
    )
    db.add(incident)
    db.flush()

    # Write sample text to uploads/txts
    txt_dir = Path("uploads") / "txts"
    txt_dir.mkdir(parents=True, exist_ok=True)
    sample_filename = f"demo_{scenario['id']}_{uuid.uuid4().hex[:8]}.txt"
    sample_path = txt_dir / sample_filename

    with open(sample_path, "w", encoding="utf-8") as f:
        f.write(scenario["sample_text"].strip())

    # Register upload
    sample_bytes = scenario["sample_text"].encode("utf-8")
    upload = Upload(
        incident_id=incident.id,
        filename=sample_filename,
        original_filename=f"{scenario['id']}_incident_report.txt",
        upload_type=UploadType.TXT,
        file_path=str(sample_path),
        file_size=len(sample_bytes),
        mime_type="text/plain",
        processed=False,
    )
    db.add(upload)
    db.flush()

    # Create workflow
    workflow = Workflow(
        incident_id=incident.id,
        status=WorkflowStatus.PENDING,
        agent_steps=[
            {"agent": "vision", "status": "pending"},
            {"agent": "ocr", "status": "pending"},
            {"agent": "knowledge", "status": "pending"},
            {"agent": "risk", "status": "pending"},
            {"agent": "simulation", "status": "pending"},
            {"agent": "recommendation", "status": "pending"},
            {"agent": "debate", "status": "pending"},
            {"agent": "report", "status": "pending"},
            {"agent": "commander", "status": "pending"},
        ],
    )
    db.add(workflow)
    db.flush()
    workflow_id = workflow.id
    incident_id = incident.id

    # Launch background pipeline
    background_tasks.add_task(_run_demo_pipeline, workflow_id=workflow_id, incident_id=incident_id)

    return workflow


async def _run_demo_pipeline(workflow_id: str, incident_id: str) -> None:
    """Background task for running the demo pipeline."""
    try:
        from app.workflow.orchestrator import run_incident_pipeline

        await run_incident_pipeline(workflow_id=workflow_id, incident_id=incident_id)
    except Exception as exc:
        from app.database.session import get_db as _get_db

        with _get_db() as db:
            workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if workflow:
                workflow.status = WorkflowStatus.FAILED
                workflow.error_message = str(exc)
