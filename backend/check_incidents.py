from app.database.session import get_db
from app.database.models import Incident

with get_db() as db:
    incidents = db.query(Incident).all()
    print(f'Total incidents: {len(incidents)}')
    for i in incidents:
        print(f'ID: {i.id}, Title: {i.title}, Type: {i.incident_type}, Uploads: {len(i.uploads)}')
