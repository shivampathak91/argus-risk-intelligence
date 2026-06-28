from app.database.session import get_db
from app.database.models import Upload
from pathlib import Path

# Delete the most recent upload for incident dd7d2a83-590d-4883-bbd1-77e9e5d50c7d
with get_db() as db:
    upload = db.query(Upload).filter(
        Upload.incident_id == "dd7d2a83-590d-4883-bbd1-77e9e5d50c7d"
    ).first()
    
    if upload:
        print(f"Deleting: {upload.original_filename} (ID: {upload.id})")
        
        # Remove file from disk
        file_path = Path(upload.file_path)
        if file_path.exists():
            file_path.unlink()
            print(f"Deleted file from disk: {file_path}")
        
        # Remove from database
        db.delete(upload)
        db.commit()
        print("Deleted from database")
    else:
        print("No upload found for this incident")
