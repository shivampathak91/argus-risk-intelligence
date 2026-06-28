from app.database.session import get_db
from app.database.models import Incident, Upload, UploadType, Workflow

with get_db() as db:
    incidents = db.query(Incident).all()
    print(f"Total incidents: {len(incidents)}")
    for i in incidents:
        print(f"  Incident: {i.id} - {i.title}")
        uploads = db.query(Upload).filter(Upload.incident_id == i.id).all()
        print(f"    Uploads: {len(uploads)}")
        for u in uploads:
            print(f"      - {u.original_filename} ({u.upload_type})")
        workflows = db.query(Workflow).filter(Workflow.incident_id == i.id).all()
        print(f"    Workflows: {len(workflows)}")
        for w in workflows:
            print(f"      - Workflow {w.id}: {w.status}")
            if w.agent_steps:
                for step in w.agent_steps:
                    print(f"        {step['agent']}: {step['status']}")
