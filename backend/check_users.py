from app.database.session import get_db
from app.database.models import User

with get_db() as db:
    users = db.query(User).all()
    print(f'Total users: {len(users)}')
    for u in users:
        print(f'ID: {u.id}, Username: {u.username}, Email: {u.email}, Role: {u.role}')
