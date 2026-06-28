from app.database.session import get_db
from app.database.models import Incident, Upload, Workflow, Report, Recommendation, Debate

with get_db() as db:
    # Find incidents by title
    incidents_to_delete = ["flood", "bridge crack found", "Road crack"]
    
    for title in incidents_to_delete:
        incident = db.query(Incident).filter(Incident.title == title).first()
        if incident:
            print(f"Deleting incident: {incident.title} (ID: {incident.id})")
            
            # Delete associated uploads first
            uploads = db.query(Upload).filter(Upload.incident_id == incident.id).all()
            for upload in uploads:
                from pathlib import Path
                file_path = Path(upload.file_path)
                if file_path.exists():
                    file_path.unlink()
                db.delete(upload)
                print(f"  Deleted upload: {upload.original_filename}")
            
            # Delete associated debates
            debates = db.query(Debate).filter(Debate.incident_id == incident.id).all()
            for debate in debates:
                db.delete(debate)
            print(f"  Deleted {len(debates)} debates")
            
            # Delete associated recommendations
            recommendations = db.query(Recommendation).filter(Recommendation.incident_id == incident.id).all()
            for rec in recommendations:
                db.delete(rec)
            print(f"  Deleted {len(recommendations)} recommendations")
            
            # Delete associated reports
            reports = db.query(Report).filter(Report.incident_id == incident.id).all()
            for report in reports:
                db.delete(report)
            print(f"  Deleted {len(reports)} reports")
            
            # Delete associated workflows
            workflows = db.query(Workflow).filter(Workflow.incident_id == incident.id).all()
            for workflow in workflows:
                db.delete(workflow)
            print(f"  Deleted {len(workflows)} workflows")
            
            # Delete incident
            db.delete(incident)
            print(f"  Deleted incident")
        else:
            print(f"Incident not found: {title}")
    
    db.commit()
    print("Done")
