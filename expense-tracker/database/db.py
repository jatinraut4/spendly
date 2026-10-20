import sqlite3
import os

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
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount NUMERIC NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
        conn.commit()

def seed_db():
    """
    Inserts sample data into the database for development purposes.
    """
    with get_db() as conn:
        # Seed users
        users = [
            ('testuser', 'hashed_password_123'),
            ('admin', 'hashed_password_456'),
            ('jane_doe', 'hashed_password_789')
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)",
            users
        )

        # Get user IDs to link expenses
        user_ids = [row['id'] for row in conn.execute("SELECT id FROM users").fetchall()]

        if not user_ids:
            return

        # Seed expenses for the first user
        primary_user_id = user_ids[0]
        expenses = [
            (primary_user_id, 50.00, 'Food', 'Grocery shopping', '2023-10-01'),
            (primary_user_id, 120.00, 'Transport', 'Fuel', '2023-10-02'),
            (primary_user_id, 15.00, 'Entertainment', 'Movie ticket', '2023-10-03'),
            (primary_user_id, 200.00, 'Utilities', 'Electricity bill', '2023-10-04'),
        ]

        # Seed expenses for the second user
        if len(user_ids) > 1:
            secondary_user_id = user_ids[1]
            expenses.extend([
                (secondary_user_id, 10.00, 'Food', 'Coffee', '2023-10-01'),
                (secondary_user_id, 60.00, 'Shopping', 'New book', '2023-10-02'),
            ])

        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
            expenses
        )
        conn.commit()
