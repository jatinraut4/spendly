import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_db, init_db, create_user
from database.queries import insert_expense, get_expense_by_id, update_expense, get_recent_transactions


@pytest.fixture
def test_db(tmp_path):
    """Set up a test database with two users and an expense."""
    import database.db as db_module
    original_db_path = db_module.DATABASE_PATH
    test_db_path = str(tmp_path / "test_edit_expense.db")
    db_module.DATABASE_PATH = test_db_path

    init_db()
    create_user("User One", "user1@example.com", "password123")
    create_user("User Two", "user2@example.com", "password123")

    with get_db() as conn:
        u1 = conn.execute("SELECT id FROM users WHERE email = ?", ("user1@example.com",)).fetchone()["id"]
        u2 = conn.execute("SELECT id FROM users WHERE email = ?", ("user2@example.com",)).fetchone()["id"]

    # Insert expense for User One
    insert_expense(u1, 50.0, "Food", "2026-03-20", "Lunch")
    with get_db() as conn:
        exp = conn.execute("SELECT id FROM expenses WHERE user_id = ?", (u1,)).fetchone()
        exp_id = exp["id"]

    yield {"user1_id": u1, "user2_id": u2, "expense_id": exp_id}

    db_module.DATABASE_PATH = original_db_path


@pytest.fixture
def client(test_db):
    """Create Flask test client with test database."""
    from app import app
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        yield client


class TestEditExpenseQueries:
    def test_get_expense_by_id_valid(self, test_db):
        """Test getting own expense by ID."""
        exp = get_expense_by_id(test_db["expense_id"], test_db["user1_id"])
        assert exp is not None
        assert exp["amount"] == 50.0
        assert exp["category"] == "Food"

    def test_get_expense_by_id_wrong_user(self, test_db):
        """Test getting another user's expense returns None."""
        exp = get_expense_by_id(test_db["expense_id"], test_db["user2_id"])
        assert exp is None

    def test_get_expense_by_id_nonexistent(self, test_db):
        """Test getting non-existent expense returns None."""
        exp = get_expense_by_id(9999, test_db["user1_id"])
        assert exp is None

    def test_update_expense_valid(self, test_db):
        """Test updating an expense successfully."""
        update_expense(test_db["expense_id"], test_db["user1_id"], 99.0, "Transport", "2026-03-21", "Gas")
        exp = get_expense_by_id(test_db["expense_id"], test_db["user1_id"])
        assert exp["amount"] == 99.0
        assert exp["category"] == "Transport"
        assert exp["date"] == "2026-03-21"
        assert exp["description"] == "Gas"

    def test_update_expense_wrong_user(self, test_db):
        """Test updating with wrong user ID does not change expense."""
        update_expense(test_db["expense_id"], test_db["user2_id"], 200.0, "Bills", "2026-03-22", "Bad edit")
        exp = get_expense_by_id(test_db["expense_id"], test_db["user1_id"])
        assert exp["amount"] == 50.0  # unchanged


class TestEditExpenseRoutes:
    def test_get_edit_expense_unauthenticated(self, client, test_db):
        """GET /expenses/<id>/edit redirects to login when logged out."""
        response = client.get(f'/expenses/{test_db["expense_id"]}/edit', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_get_edit_expense_authenticated_owner(self, client, test_db):
        """GET /expenses/<id>/edit returns 200 and pre-filled form for owner."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db["user1_id"]

        response = client.get(f'/expenses/{test_db["expense_id"]}/edit')
        assert response.status_code == 200
        assert b'Edit Expense' in response.data
        assert b'50.0' in response.data
        assert b'Food' in response.data

    def test_get_edit_expense_other_user(self, client, test_db):
        """GET /expenses/<id>/edit returns 404 for another user's expense."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db["user2_id"]

        response = client.get(f'/expenses/{test_db["expense_id"]}/edit')
        assert response.status_code == 404

    def test_get_edit_expense_nonexistent(self, client, test_db):
        """GET /expenses/<id>/edit returns 404 for non-existent expense."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db["user1_id"]

        response = client.get('/expenses/9999/edit')
        assert response.status_code == 404

    def test_post_edit_expense_unauthenticated(self, client, test_db):
        """POST /expenses/<id>/edit redirects to login when logged out."""
        response = client.post(f'/expenses/{test_db["expense_id"]}/edit', data={
            'amount': '80.0',
            'category': 'Bills',
            'date': '2026-03-25',
            'description': 'Internet'
        }, follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_post_edit_expense_valid(self, client, test_db):
        """POST /expenses/<id>/edit with valid data updates expense and redirects to profile."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db["user1_id"]

        response = client.post(f'/expenses/{test_db["expense_id"]}/edit', data={
            'amount': '120.00',
            'category': 'Health',
            'date': '2026-03-25',
            'description': 'Checkup'
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/profile' in response.headers['Location']

        exp = get_expense_by_id(test_db["expense_id"], test_db["user1_id"])
        assert exp['amount'] == 120.0
        assert exp['category'] == 'Health'
        assert exp['date'] == '2026-03-25'
        assert exp['description'] == 'Checkup'

    def test_post_edit_expense_other_user(self, client, test_db):
        """POST /expenses/<id>/edit returns 404 for another user's expense."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db["user2_id"]

        response = client.post(f'/expenses/{test_db["expense_id"]}/edit', data={
            'amount': '100.0',
            'category': 'Food',
            'date': '2026-03-25',
            'description': 'Hacked'
        })
        assert response.status_code == 404

    def test_post_edit_expense_missing_amount(self, client, test_db):
        """POST /expenses/<id>/edit with missing amount re-renders form with error."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db["user1_id"]

        response = client.post(f'/expenses/{test_db["expense_id"]}/edit', data={
            'amount': '',
            'category': 'Food',
            'date': '2026-03-25',
            'description': 'Test'
        })
        assert response.status_code == 200
        assert b'Amount is required' in response.data

    def test_post_edit_expense_zero_amount(self, client, test_db):
        """POST /expenses/<id>/edit with zero amount re-renders form with error."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db["user1_id"]

        response = client.post(f'/expenses/{test_db["expense_id"]}/edit', data={
            'amount': '0',
            'category': 'Food',
            'date': '2026-03-25',
            'description': 'Test'
        })
        assert response.status_code == 200
        assert b'positive number' in response.data

    def test_post_edit_expense_invalid_category(self, client, test_db):
        """POST /expenses/<id>/edit with invalid category re-renders form with error."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db["user1_id"]

        response = client.post(f'/expenses/{test_db["expense_id"]}/edit', data={
            'amount': '50.0',
            'category': 'Crypto',
            'date': '2026-03-25',
            'description': 'Test'
        })
        assert response.status_code == 200
        assert b'Invalid category selected' in response.data

    def test_post_edit_expense_invalid_date(self, client, test_db):
        """POST /expenses/<id>/edit with invalid date format re-renders form with error."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db["user1_id"]

        response = client.post(f'/expenses/{test_db["expense_id"]}/edit', data={
            'amount': '50.0',
            'category': 'Food',
            'date': 'not-a-date',
            'description': 'Test'
        })
        assert response.status_code == 200
        assert b'Invalid date format' in response.data

    def test_post_edit_expense_no_description(self, client, test_db):
        """POST /expenses/<id>/edit with empty description stores NULL."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db["user1_id"]

        response = client.post(f'/expenses/{test_db["expense_id"]}/edit', data={
            'amount': '60.0',
            'category': 'Food',
            'date': '2026-03-25',
            'description': ''
        }, follow_redirects=False)

        assert response.status_code == 302
        exp = get_expense_by_id(test_db["expense_id"], test_db["user1_id"])
        assert exp['description'] is None
