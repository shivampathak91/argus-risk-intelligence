from app.database.session import get_db
from app.database.models import Upload

with get_db() as db:
    uploads = db.query(Upload).all()
    for u in uploads:
        print(f'ID: {u.id}, Original: {u.original_filename}, Incident: {u.incident_id}')
