import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_db, init_db, create_user
from database.queries import insert_expense, delete_expense, get_expense_by_id, get_recent_transactions


@pytest.fixture
def test_db(tmp_path):
    """Set up test database and test users."""
    import database.db as db_module
    original_db_path = db_module.DATABASE_PATH
    db_module.DATABASE_PATH = str(tmp_path / "test_delete_expense.db")

    init_db()
    create_user("User One", "user1@example.com", "password123")
    create_user("User Two", "user2@example.com", "password123")

    with get_db() as conn:
        u1 = conn.execute("SELECT id FROM users WHERE email = ?", ("user1@example.com",)).fetchone()["id"]
        u2 = conn.execute("SELECT id FROM users WHERE email = ?", ("user2@example.com",)).fetchone()["id"]

    yield {"u1": u1, "u2": u2}

    db_module.DATABASE_PATH = original_db_path


@pytest.fixture
def client(test_db):
    """Create Flask test client."""
    from app import app
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        yield client


class TestDeleteExpenseUnit:
    def test_delete_expense_valid(self, test_db):
        """delete_expense removes the row when given correct id and user_id."""
        u1 = test_db["u1"]
        insert_expense(u1, 50.0, "Food", "2026-03-20", "Lunch")

        txs = get_recent_transactions(u1)
        assert len(txs) == 1

        with get_db() as conn:
            row = conn.execute("SELECT id FROM expenses WHERE user_id = ?", (u1,)).fetchone()
            expense_id = row["id"]

        delete_expense(expense_id, u1)

        txs_after = get_recent_transactions(u1)
        assert len(txs_after) == 0

    def test_delete_expense_wrong_user(self, test_db):
        """delete_expense does not remove row if user_id does not match ownership."""
        u1 = test_db["u1"]
        u2 = test_db["u2"]
        insert_expense(u1, 50.0, "Food", "2026-03-20", "Lunch")

        with get_db() as conn:
            row = conn.execute("SELECT id FROM expenses WHERE user_id = ?", (u1,)).fetchone()
            expense_id = row["id"]

        delete_expense(expense_id, u2) # wrong user

        txs = get_recent_transactions(u1)
        assert len(txs) == 1

    def test_delete_expense_non_existent(self, test_db):
        """delete_expense with non-existent id does not raise error."""
        u1 = test_db["u1"]
        delete_expense(9999, u1)


class TestDeleteExpenseRoutes:
    def test_post_delete_unauthenticated(self, client):
        """POST /expenses/<id>/delete unauthenticated redirects to /login (302)."""
        response = client.post('/expenses/1/delete', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_post_delete_authenticated_own_expense(self, client, test_db):
        """POST /expenses/<id>/delete authenticated for own expense deletes it and redirects to profile."""
        u1 = test_db["u1"]
        insert_expense(u1, 50.0, "Food", "2026-03-20", "Lunch")

        with get_db() as conn:
            row = conn.execute("SELECT id FROM expenses WHERE user_id = ?", (u1,)).fetchone()
            expense_id = row["id"]

        with client.session_transaction() as sess:
            sess['user_id'] = u1

        response = client.post(f'/expenses/{expense_id}/delete', follow_redirects=False)
        assert response.status_code == 302
        assert '/profile' in response.headers['Location']

        assert get_expense_by_id(expense_id, u1) is None

    def test_post_delete_authenticated_other_users_expense(self, client, test_db):
        """POST /expenses/<id>/delete for other user's expense returns 404."""
        u1 = test_db["u1"]
        u2 = test_db["u2"]
        insert_expense(u1, 50.0, "Food", "2026-03-20", "Lunch")

        with get_db() as conn:
            row = conn.execute("SELECT id FROM expenses WHERE user_id = ?", (u1,)).fetchone()
            expense_id = row["id"]

        with client.session_transaction() as sess:
            sess['user_id'] = u2

        response = client.post(f'/expenses/{expense_id}/delete')
        assert response.status_code == 404
        assert get_expense_by_id(expense_id, u1) is not None

    def test_post_delete_non_existent_expense(self, client, test_db):
        """POST /expenses/<id>/delete for non-existent expense returns 404."""
        u1 = test_db["u1"]
        with client.session_transaction() as sess:
            sess['user_id'] = u1

        response = client.post('/expenses/9999/delete')
        assert response.status_code == 404

    def test_get_delete_method_not_allowed(self, client, test_db):
        """GET /expenses/<id>/delete returns 405 Method Not Allowed."""
        u1 = test_db["u1"]
        insert_expense(u1, 50.0, "Food", "2026-03-20", "Lunch")

        with get_db() as conn:
            row = conn.execute("SELECT id FROM expenses WHERE user_id = ?", (u1,)).fetchone()
            expense_id = row["id"]

        with client.session_transaction() as sess:
            sess['user_id'] = u1

        response = client.get(f'/expenses/{expense_id}/delete')
        assert response.status_code == 405
