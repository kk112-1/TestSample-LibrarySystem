from app import create_app
from app.db import get_db
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    db = get_db()
    
    # 1. Clear users
    db.execute('DELETE FROM user')
    db.execute('DELETE FROM sqlite_sequence WHERE name="user"')

    # 2. Add Users
    users = [
        ('admin', 'adminpass', 'admin'),
        ('user01', 'password', 'user'),
        ('user02', 'password', 'user'),
    ]
    
    for username, password, role in users:
        db.execute(
            'INSERT INTO user (username, password, role) VALUES (?, ?, ?)',
            (username, generate_password_hash(password), role)
        )
        
    # 3. Clear books
    db.execute('DELETE FROM book')
    db.execute('DELETE FROM sqlite_sequence WHERE name="book"')
    
    # 4. Add Books
    books = [
        ('Python入門', '978-4-0000-0001-1', 'Guido', 'OReilly', 5),
        ('Flask Web開発', '978-4-0000-0002-8', 'Miguel', 'OReilly', 3),
        ('SQLアンチパターン', '978-4-0000-0003-5', 'Bill', 'OReilly', 2),
        ('リーダブルコード', '978-4-0000-0004-2', 'Boswell', 'OReilly', 0), # No stock
        ('人月の神話', '978-4-0000-0005-9', 'Brooks', 'Pearson', 1),
        ('達人プログラマー', '978-4-0000-0006-6', 'Andrew', 'Ohmsha', 2),
        ('Clean Code', '978-4-0000-0007-3', 'Martin', 'Pearson', 2),
        ('テスト駆動開発', '978-4-0000-0008-0', 'Kent', 'Ohmsha', 2),
    ]

    for title, isbn, author, publisher, stock in books:
        db.execute(
            'INSERT INTO book (title, isbn, author, publisher, stock_count) VALUES (?, ?, ?, ?, ?)',
            (title, isbn, author, publisher, stock)
        )
        
    # 5. Clear loans
    db.execute('DELETE FROM loan')
    db.execute('DELETE FROM sqlite_sequence WHERE name="loan"')

    db.commit()
    print("Seeded database with initial data.")
