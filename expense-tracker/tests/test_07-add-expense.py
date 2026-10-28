import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_db, init_db, create_user
from database.queries import insert_expense, get_recent_transactions


@pytest.fixture
def test_db(tmp_path):
    """Set up test database and test user."""
    import database.db as db_module
    original_db_path = db_module.DATABASE_PATH
    db_module.DATABASE_PATH = str(tmp_path / "test_spec_07.db")

    init_db()
    create_user("Test User", "test@example.com", "password123")

    with get_db() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", ("test@example.com",)).fetchone()
        user_id = user["id"]

    yield user_id

    db_module.DATABASE_PATH = original_db_path


@pytest.fixture
def client(test_db):
    """Create Flask test client."""
    from app import app
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        yield client


class TestInsertExpenseSpec:
    def test_insert_expense_valid_row(self, test_db):
        """Validates insert_expense inserts a row correctly when valid parameters are passed."""
        insert_expense(test_db, 50.0, "Food", "2026-03-20", "Lunch")
        with get_db() as conn:
            row = conn.execute("SELECT * FROM expenses WHERE user_id = ?", (test_db,)).fetchone()
            assert row is not None
            assert row["amount"] == 50.0
            assert row["category"] == "Food"
            assert row["date"] == "2026-03-20"
            assert row["description"] == "Lunch"

    def test_insert_expense_null_description(self, test_db):
        """Validates insert_expense stores description as NULL when description=None."""
        insert_expense(test_db, 25.0, "Transport", "2026-03-21", None)
        with get_db() as conn:
            row = conn.execute("SELECT * FROM expenses WHERE user_id = ?", (test_db,)).fetchone()
            assert row is not None
            assert row["description"] is None


class TestAddExpenseRouteSpec:
    def test_get_add_expense_unauthenticated(self, client):
        """GET /expenses/add when unauthenticated redirects to /login (302)."""
        response = client.get('/expenses/add', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_get_add_expense_authenticated(self, client, test_db):
        """GET /expenses/add when authenticated returns 200, category select with 7 options, and POST form."""
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
        """POST /expenses/add when unauthenticated redirects to /login (302)."""
        response = client.post('/expenses/add', data={
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        }, follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_post_add_expense_valid_data(self, client, test_db):
        """POST /expenses/add with valid data redirects to /profile (302) and inserts expense row."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db

        response = client.post('/expenses/add', data={
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/profile' in response.headers['Location']

        txs = get_recent_transactions(test_db)
        assert len(txs) == 1
        assert txs[0]['amount'] == '50.00'
        assert txs[0]['category'] == 'Food'

    def test_post_add_expense_missing_amount(self, client, test_db):
        """POST /expenses/add with missing amount returns 200 and error message."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db

        response = client.post('/expenses/add', data={
            'amount': '',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })
        assert response.status_code == 200
        assert b'Amount is required' in response.data

    def test_post_add_expense_zero_amount(self, client, test_db):
        """POST /expenses/add with amount = 0 returns 200 and error message."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db

        response = client.post('/expenses/add', data={
            'amount': '0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })
        assert response.status_code == 200
        assert b'positive number' in response.data

    def test_post_add_expense_non_numeric_amount(self, client, test_db):
        """POST /expenses/add with non-numeric amount returns 200 and error message."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db

        response = client.post('/expenses/add', data={
            'amount': 'abc',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })
        assert response.status_code == 200
        assert b'valid number' in response.data

    def test_post_add_expense_invalid_category(self, client, test_db):
        """POST /expenses/add with invalid category returns 200 and error message."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db

        response = client.post('/expenses/add', data={
            'amount': '50.0',
            'category': 'NotACategory',
            'date': '2026-03-20',
            'description': 'Lunch'
        })
        assert response.status_code == 200
        assert b'Invalid category' in response.data

    def test_post_add_expense_invalid_date(self, client, test_db):
        """POST /expenses/add with invalid date string returns 200 and error message."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db

        response = client.post('/expenses/add', data={
            'amount': '50.0',
            'category': 'Food',
            'date': 'invalid-date',
            'description': 'Lunch'
        })
        assert response.status_code == 200
        assert b'Invalid date' in response.data

    def test_post_add_expense_no_description(self, client, test_db):
        """POST /expenses/add without description (optional) redirects to /profile (302) and saves with NULL description."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_db

        response = client.post('/expenses/add', data={
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': ''
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/profile' in response.headers['Location']

        with get_db() as conn:
            row = conn.execute("SELECT description FROM expenses WHERE user_id = ?", (test_db,)).fetchone()
            assert row["description"] is None
