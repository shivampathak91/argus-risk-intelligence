from app.database.session import get_db
from app.database.models import Upload
from pathlib import Path

with get_db() as db:
    uploads = db.query(Upload).all()
    print(f"Found {len(uploads)} uploads")
    
    for upload in uploads:
        print(f"Deleting: {upload.original_filename} (ID: {upload.id})")
        
        # Remove file from disk
        file_path = Path(upload.file_path)
        if file_path.exists():
            file_path.unlink()
            print(f"  Deleted file from disk: {file_path}")
        
        # Remove from database
        db.delete(upload)
    
    db.commit()
    print(f"Deleted {len(uploads)} uploads from database")
