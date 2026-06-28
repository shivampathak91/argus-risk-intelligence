from app.database.session import get_db
from app.database.models import Workflow

with get_db() as db:
    workflows = db.query(Workflow).filter(Workflow.incident_id == "fd8d049d-00af-4db3-8243-dc85eaddb319").all()
    for w in workflows:
        db.delete(w)
    db.commit()
