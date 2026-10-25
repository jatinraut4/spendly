import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_PATH = 'spendly.db'

def get_db():
    """
    Returns a SQLite connection with row_factory set to sqlite3.Row
    and foreign keys enabled.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """
    Initializes the database schema by creating the users and expenses tables.
    """
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
        conn.commit()

def create_user(name, email, password):
    """
    Creates a new user in the database with a hashed password.
    """
    password_hash = generate_password_hash(password)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash)
        )
        conn.commit()

def verify_user(email, password):
    """
    Verifies user credentials and returns the user record if valid.
    Returns None if credentials are invalid.
    """
    with get_db() as conn:
        user = conn.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            return dict(user)
        return None

def get_user_by_id(user_id):
    """
    Fetches a user by their ID.
    Returns the user record as a dict or None if not found.
    """
    with get_db() as conn:
        user = conn.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        return dict(user) if user else None

def seed_db():

    """
    Inserts sample data into the database for development purposes.
    Prevents duplicate seeding if users already exist.
    """
    with get_db() as conn:
        # Check if users table already contains data
        if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            return

        # Seed demo user
        demo_user = (
            "Demo User",
            "demo@spendly.com",
            generate_password_hash("demo123")
        )
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            demo_user
        )
        user_id = cursor.lastrowid

        # Seed 8 sample expenses across all required categories
        # Categories: Food, Transport, Bills, Health, Entertainment, Shopping, Other
        expenses = [
            (user_id, 15.50, 'Food', 'Lunch at Deli', '2023-10-01'),
            (user_id, 42.00, 'Transport', 'Gas Refill', '2023-10-02'),
            (user_id, 120.00, 'Bills', 'Electric Bill', '2023-10-03'),
            (user_id, 25.00, 'Health', 'Pharmacy', '2023-10-04'),
            (user_id, 12.00, 'Entertainment', 'Streaming Sub', '2023-10-05'),
            (user_id, 85.00, 'Shopping', 'New Shoes', '2023-10-06'),
            (user_id, 10.00, 'Other', 'Parking Fee', '2023-10-07'),
            (user_id, 22.00, 'Food', 'Dinner Out', '2023-10-08'),
        ]

        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            expenses
        )
        conn.commit()
