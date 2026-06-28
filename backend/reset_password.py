from app.database.session import get_db
from app.database.models import User
from app.core.security import hash_password

with get_db() as db:
    user = db.query(User).filter(User.email == "admin@argus.defense").first()
    if user:
        user.hashed_password = hash_password("password123")
        db.commit()
        print(f"Password reset for user: {user.email} (username: {user.username})")
    else:
        print("User not found")
