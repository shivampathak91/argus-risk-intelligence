from app.database.session import get_db
from app.database.models import User, UserRole
from app.core.security import hash_password

with get_db() as db:
    # Check if test user exists
    existing = db.query(User).filter(User.username == 'testuser').first()
    if existing:
        print('Test user already exists')
        print(f'Username: testuser, Password: test123')
    else:
        user = User(
            username='testuser',
            email='testuser@example.com',
            hashed_password=hash_password('test123'),
            full_name='Test User',
            role=UserRole.ANALYST,
        )
        db.add(user)
        db.commit()
        print('Test user created successfully')
        print(f'Username: testuser, Password: test123')
