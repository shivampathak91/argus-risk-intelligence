from app.database.session import get_db
from app.database.models import Incident, Upload

with get_db() as db:
    incidents = db.query(Incident).all()
    for i in incidents:
        if i.uploads:
            print(f'\nIncident: {i.title} (ID: {i.id})')
            for u in i.uploads:
                print(f'  Upload: {u.original_filename}, Type: {u.upload_type}, Path: {u.file_path}')
