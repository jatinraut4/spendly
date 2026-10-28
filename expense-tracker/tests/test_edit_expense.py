import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_db, init_db, create_user
from database.queries import insert_expense, get_expense_by_id, update_expense, get_recent_transactions


@pytest.fixture
def test_db(tmp_path):
    """Set up test database and test users and expenses."""
    import database.db as db_module
    original_db_path = db_module.DATABASE_PATH
    db_module.DATABASE_PATH = str(tmp_path / "test_spec_08.db")

    init_db()
    create_user("User One", "user1@example.com", "password123")
    create_user("User Two", "user2@example.com", "password123")

    with get_db() as conn:
        u1 = conn.execute("SELECT id FROM users WHERE email = ?", ("user1@example.com",)).fetchone()["id"]
        u2 = conn.execute("SELECT id FROM users WHERE email = ?", ("user2@example.com",)).fetchone()["id"]

        # Insert expense for user 1
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (u1, 100.0, "Food", "2026-03-20", "Grocery")
        )
        exp1 = conn.execute("SELECT id FROM expenses WHERE user_id = ?", (u1,)).fetchone()["id"]

        # Insert expense for user 2
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (u2, 200.0, "Transport", "2026-03-21", "Bus pass")
        )
        exp2 = conn.execute("SELECT id FROM expenses WHERE user_id = ?", (u2,)).fetchone()["id"]
        conn.commit()

    yield {"u1": u1, "u2": u2, "exp1": exp1, "exp2": exp2}

    db_module.DATABASE_PATH = original_db_path


@pytest.fixture
def client(test_db):
    """Create Flask test client."""
    from app import app
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        yield client


class TestEditExpenseQueries:
    def test_get_expense_by_id_valid(self, test_db):
        """get_expense_by_id returns the matching row for the correct user."""
        row = get_expense_by_id(test_db["exp1"], test_db["u1"])
        assert row is not None
        assert row["id"] == test_db["exp1"]
        assert row["amount"] == 100.0
        assert row["category"] == "Food"

    def test_get_expense_by_id_wrong_user(self, test_db):
        """get_expense_by_id returns None when requested with wrong user_id."""
        row = get_expense_by_id(test_db["exp1"], test_db["u2"])
        assert row is None

    def test_get_expense_by_id_nonexistent(self, test_db):
        """get_expense_by_id returns None for non-existent expense id."""
        row = get_expense_by_id(9999, test_db["u1"])
        assert row is None

    def test_update_expense_valid(self, test_db):
        """update_expense successfully updates the expense row."""
        update_expense(test_db["exp1"], test_db["u1"], 150.0, "Bills", "2026-03-22", "Electricity")
        row = get_expense_by_id(test_db["exp1"], test_db["u1"])
        assert row["amount"] == 150.0
        assert row["category"] == "Bills"
        assert row["date"] == "2026-03-22"
        assert row["description"] == "Electricity"

    def test_update_expense_wrong_user(self, test_db):
        """update_expense leaves row unchanged if wrong user_id is provided."""
        update_expense(test_db["exp1"], test_db["u2"], 999.0, "Shopping", "2026-03-25", "Hacked")
        row = get_expense_by_id(test_db["exp1"], test_db["u1"])
        assert row["amount"] == 100.0
        assert row["category"] == "Food"


class TestEditExpenseRoute:
    def test_get_edit_expense_unauthenticated(self, client, test_db):
        """GET /expenses/<id>/edit when unauthenticated redirects to /login (302)."""
        response = client.get(f'/expenses/{test_db["exp1"]}/edit', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_get_edit_expense_authenticated_own(self, client, test_db):
        """GET /expenses/<id>/edit when authenticated and own expense returns 200 with pre-filled form."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db['u1']

        response = client.get(f'/expenses/{test_db["exp1"]}/edit')
        assert response.status_code == 200
        assert b'Edit Expense' in response.data
        assert b'100.0' in response.data
        assert b'Food' in response.data

    def test_get_edit_expense_other_user(self, client, test_db):
        """GET /expenses/<id>/edit for another user's expense returns 404."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db['u1']

        response = client.get(f'/expenses/{test_db["exp2"]}/edit')
        assert response.status_code == 404

    def test_get_edit_expense_nonexistent(self, client, test_db):
        """GET /expenses/<id>/edit for non-existent expense returns 404."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db['u1']

        response = client.get('/expenses/9999/edit')
        assert response.status_code == 404

    def test_post_edit_expense_unauthenticated(self, client, test_db):
        """POST /expenses/<id>/edit when unauthenticated redirects to /login (302)."""
        response = client.post(f'/expenses/{test_db["exp1"]}/edit', data={
            'amount': '150.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Updated'
        }, follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_post_edit_expense_valid_data(self, client, test_db):
        """POST /expenses/<id>/edit with valid data redirects to /profile (302) and updates row."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db['u1']

        response = client.post(f'/expenses/{test_db["exp1"]}/edit', data={
            'amount': '175.50',
            'category': 'Shopping',
            'date': '2026-03-22',
            'description': 'New clothes'
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/profile' in response.headers['Location']

        row = get_expense_by_id(test_db["exp1"], test_db["u1"])
        assert row["amount"] == 175.50
        assert row["category"] == "Shopping"
        assert row["description"] == "New clothes"

    def test_post_edit_expense_other_user(self, client, test_db):
        """POST /expenses/<id>/edit on another user's expense returns 404."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db['u1']

        response = client.post(f'/expenses/{test_db["exp2"]}/edit', data={
            'amount': '175.50',
            'category': 'Shopping',
            'date': '2026-03-22',
            'description': 'Hacked'
        })
        assert response.status_code == 404

    def test_post_edit_expense_missing_amount(self, client, test_db):
        """POST /expenses/<id>/edit with missing amount returns 200 and error message."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db['u1']

        response = client.post(f'/expenses/{test_db["exp1"]}/edit', data={
            'amount': '',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Test'
        })
        assert response.status_code == 200
        assert b'Amount is required' in response.data

    def test_post_edit_expense_zero_amount(self, client, test_db):
        """POST /expenses/<id>/edit with amount = 0 returns 200 and error message."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db['u1']

        response = client.post(f'/expenses/{test_db["exp1"]}/edit', data={
            'amount': '0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Test'
        })
        assert response.status_code == 200
        assert b'positive number' in response.data

    def test_post_edit_expense_non_numeric_amount(self, client, test_db):
        """POST /expenses/<id>/edit with non-numeric amount returns 200 and error message."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db['u1']

        response = client.post(f'/expenses/{test_db["exp1"]}/edit', data={
            'amount': 'abc',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Test'
        })
        assert response.status_code == 200
        assert b'valid number' in response.data

    def test_post_edit_expense_invalid_category(self, client, test_db):
        """POST /expenses/<id>/edit with invalid category returns 200 and error message."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db['u1']

        response = client.post(f'/expenses/{test_db["exp1"]}/edit', data={
            'amount': '50.0',
            'category': 'InvalidCat',
            'date': '2026-03-20',
            'description': 'Test'
        })
        assert response.status_code == 200
        assert b'Invalid category' in response.data

    def test_post_edit_expense_invalid_date(self, client, test_db):
        """POST /expenses/<id>/edit with invalid date format returns 200 and error message."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db['u1']

        response = client.post(f'/expenses/{test_db["exp1"]}/edit', data={
            'amount': '50.0',
            'category': 'Food',
            'date': 'bad-date',
            'description': 'Test'
        })
        assert response.status_code == 200
        assert b'Invalid date' in response.data

    def test_post_edit_expense_no_description(self, client, test_db):
        """POST /expenses/<id>/edit without description redirects to /profile and saves with NULL description."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db['u1']

        response = client.post(f'/expenses/{test_db["exp1"]}/edit', data={
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': ''
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/profile' in response.headers['Location']

        row = get_expense_by_id(test_db["exp1"], test_db["u1"])
        assert row["description"] is None
