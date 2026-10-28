import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_db, init_db, create_user
from database.queries import insert_expense, get_recent_transactions


@pytest.fixture
def test_db(tmp_path):
    """Set up a test database with a user."""
    import database.db as db_module
    original_db_path = db_module.DATABASE_PATH
    test_db_path = str(tmp_path / "test_add_expense.db")
    db_module.DATABASE_PATH = test_db_path

    init_db()
    create_user("Test User", "test@example.com", "password123")

    with get_db() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", ("test@example.com",)).fetchone()
        user_id = user["id"]

    yield user_id

    db_module.DATABASE_PATH = original_db_path


@pytest.fixture
def client(test_db):
    """Create Flask test client with test database."""
    from app import app
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        yield client


class TestInsertExpense:
    def test_insert_expense_valid(self, test_db):
        """Test inserting a valid expense with description."""
        user_id = test_db
        insert_expense(user_id, 50.0, "Food", "2026-03-20", "Lunch")

        with get_db() as conn:
            row = conn.execute("SELECT * FROM expenses WHERE user_id = ?", (user_id,)).fetchone()
            assert row is not None
            assert row["amount"] == 50.0
            assert row["category"] == "Food"
            assert row["date"] == "2026-03-20"
            assert row["description"] == "Lunch"

    def test_insert_expense_null_description(self, test_db):
        """Test inserting an expense with None description."""
        user_id = test_db
        insert_expense(user_id, 25.0, "Transport", "2026-03-21", None)

        with get_db() as conn:
            row = conn.execute("SELECT * FROM expenses WHERE user_id = ?", (user_id,)).fetchone()
            assert row is not None
            assert row["description"] is None


class TestAddExpenseRoutes:
    def test_get_add_expense_unauthenticated(self, client):
        """GET /expenses/add redirects to login when logged out."""
        response = client.get('/expenses/add', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_get_add_expense_authenticated(self, client, test_db):
        """GET /expenses/add returns 200 and category select options when logged in."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db

        response = client.get('/expenses/add')
        assert response.status_code == 200
        assert b'Food' in response.data
        assert b'Transport' in response.data
        assert b'Bills' in response.data
        assert b'Health' in response.data
        assert b'Entertainment' in response.data
        assert b'Shopping' in response.data
        assert b'Other' in response.data
        assert b'method="POST"' in response.data

    def test_post_add_expense_unauthenticated(self, client):
        """POST /expenses/add redirects to login when logged out."""
        response = client.post('/expenses/add', data={
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        }, follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_post_add_expense_valid(self, client, test_db):
        """POST /expenses/add with valid data redirects to profile and inserts row."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db

        response = client.post('/expenses/add', data={
            'amount': '75.50',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Dinner'
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/profile' in response.headers['Location']

        txs = get_recent_transactions(test_db)
        assert len(txs) == 1
        assert txs[0]['category'] == 'Food'
        assert txs[0]['amount'] == '75.50'

    def test_post_add_expense_missing_amount(self, client, test_db):
        """POST /expenses/add with missing amount re-renders form with error."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db

        response = client.post('/expenses/add', data={
            'amount': '',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Test'
        })
        assert response.status_code == 200
        assert b'Amount is required' in response.data

    def test_post_add_expense_zero_amount(self, client, test_db):
        """POST /expenses/add with zero amount re-renders form with error."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db

        response = client.post('/expenses/add', data={
            'amount': '0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Test'
        })
        assert response.status_code == 200
        assert b'positive number' in response.data

    def test_post_add_expense_non_numeric_amount(self, client, test_db):
        """POST /expenses/add with non-numeric amount re-renders form with error."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db

        response = client.post('/expenses/add', data={
            'amount': 'abc',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Test'
        })
        assert response.status_code == 200
        assert b'valid number' in response.data

    def test_post_add_expense_invalid_category(self, client, test_db):
        """POST /expenses/add with invalid category re-renders form with error."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db

        response = client.post('/expenses/add', data={
            'amount': '50.0',
            'category': 'InvalidCat',
            'date': '2026-03-20',
            'description': 'Test'
        })
        assert response.status_code == 200
        assert b'Invalid category' in response.data

    def test_post_add_expense_invalid_date(self, client, test_db):
        """POST /expenses/add with invalid date string re-renders form with error."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db

        response = client.post('/expenses/add', data={
            'amount': '50.0',
            'category': 'Food',
            'date': 'not-a-date',
            'description': 'Test'
        })
        assert response.status_code == 200
        assert b'Invalid date' in response.data

    def test_post_add_expense_no_description(self, client, test_db):
        """POST /expenses/add without optional description succeeds."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db

        response = client.post('/expenses/add', data={
            'amount': '30.0',
            'category': 'Transport',
            'date': '2026-03-20',
            'description': ''
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/profile' in response.headers['Location']
