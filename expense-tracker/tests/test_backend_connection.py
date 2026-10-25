import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_db, init_db, create_user
from database.queries import get_summary_stats, get_recent_transactions, get_category_breakdown


@pytest.fixture
def test_db(tmp_path):
    """Set up a test database with sample data."""
    # Use temporary file for testing
    import database.db as db_module
    original_db_path = db_module.DATABASE_PATH
    test_db_path = str(tmp_path / "test.db")
    db_module.DATABASE_PATH = test_db_path

    # Initialize database
    init_db()

    # Create test user
    create_user("Test User", "test@example.com", "password123")

    # Get user_id
    with get_db() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", ("test@example.com",)).fetchone()
        user_id = user["id"]

        # Add sample expenses
        expenses = [
            (user_id, 100.00, 'Food', '2023-10-08', 'Groceries'),
            (user_id, 50.00, 'Transport', '2023-10-07', 'Gas'),
            (user_id, 200.00, 'Bills', '2023-10-06', 'Electric Bill'),
            (user_id, 75.00, 'Food', '2023-10-05', 'Restaurant'),
            (user_id, 30.00, 'Entertainment', '2023-10-04', 'Movie'),
            (user_id, 120.00, 'Shopping', '2023-10-03', 'Clothes'),
            (user_id, 25.00, 'Health', '2023-10-02', 'Pharmacy'),
            (user_id, 150.00, 'Bills', '2023-10-01', 'Internet'),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            expenses
        )
        conn.commit()

    yield user_id

    # Restore original database path
    db_module.DATABASE_PATH = original_db_path


@pytest.fixture
def empty_user_db(tmp_path):
    """Set up a test database with a user but no expenses."""
    import database.db as db_module
    original_db_path = db_module.DATABASE_PATH
    test_db_path = str(tmp_path / "empty_test.db")
    db_module.DATABASE_PATH = test_db_path

    init_db()
    create_user("Empty User", "empty@example.com", "password123")

    with get_db() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", ("empty@example.com",)).fetchone()
        user_id = user["id"]

    yield user_id

    db_module.DATABASE_PATH = original_db_path


class TestGetSummaryStats:
    def test_with_expenses(self, test_db):
        """Test summary stats calculation with expenses."""
        user_id = test_db
        stats = get_summary_stats(user_id)

        assert "total_spent" in stats
        assert "count" in stats
        assert "top_category" in stats

        # Total should be 750.00 (sum of all expenses)
        assert stats["total_spent"] == "750.00"
        assert stats["count"] == 8

        # Bills has highest total: 200 + 150 = 350
        assert stats["top_category"] == "Bills"

    def test_with_no_expenses(self, empty_user_db):
        """Test summary stats with no expenses."""
        user_id = empty_user_db
        stats = get_summary_stats(user_id)

        assert stats["total_spent"] == "0.00"
        assert stats["count"] == 0
        assert stats["top_category"] == "—"


class TestGetRecentTransactions:
    def test_with_expenses(self, test_db):
        """Test fetching recent transactions."""
        user_id = test_db
        transactions = get_recent_transactions(user_id, limit=5)

        assert len(transactions) == 5

        # Check structure of first transaction
        tx = transactions[0]
        assert "date" in tx
        assert "description" in tx
        assert "category" in tx
        assert "category_class" in tx
        assert "amount" in tx

        # Should be ordered newest-first (2023-10-08 is most recent)
        assert transactions[0]["date"] == "2023-10-08"
        assert transactions[0]["description"] == "Groceries"
        assert transactions[0]["category"] == "Food"
        assert transactions[0]["amount"] == "100.00"

    def test_with_no_expenses(self, empty_user_db):
        """Test fetching transactions with no expenses."""
        user_id = empty_user_db
        transactions = get_recent_transactions(user_id)

        assert transactions == []

    def test_limit_parameter(self, test_db):
        """Test that limit parameter works correctly."""
        user_id = test_db
        transactions = get_recent_transactions(user_id, limit=3)

        assert len(transactions) == 3


class TestGetCategoryBreakdown:
    def test_with_expenses(self, test_db):
        """Test category breakdown calculation."""
        user_id = test_db
        categories = get_category_breakdown(user_id)

        # Should have 6 unique categories
        assert len(categories) == 6

        # Check structure
        cat = categories[0]
        assert "name" in cat
        assert "amount" in cat
        assert "percentage" in cat

        # First category should be Bills (highest: 350.00)
        assert categories[0]["name"] == "Bills"
        assert categories[0]["amount"] == "350.00"

        # Percentages should be integers
        for cat in categories:
            assert isinstance(cat["percentage"], int)

        # Percentages should sum to 100
        total_pct = sum(cat["percentage"] for cat in categories)
        assert total_pct == 100

    def test_with_no_expenses(self, empty_user_db):
        """Test category breakdown with no expenses."""
        user_id = empty_user_db
        categories = get_category_breakdown(user_id)

        assert categories == []


class TestRouteIntegration:
    """Test the /profile route with real data."""

    @pytest.fixture
    def client(self):
        """Create a Flask test client."""
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_profile_unauthenticated(self, client):
        """Test that unauthenticated users are redirected."""
        response = client.get('/profile')
        assert response.status_code == 302
        assert response.location.endswith('/login')

    def test_profile_authenticated(self, client):
        """Test profile page with authenticated user."""
        # Register and login a test user
        client.post('/register', data={
            'name': 'Route Test User',
            'email': 'routetest@example.com',
            'password': 'testpass123',
            'confirm_password': 'testpass123'
        })

        client.post('/login', data={
            'email': 'routetest@example.com',
            'password': 'testpass123'
        })

        # Access profile
        response = client.get('/profile')
        assert response.status_code == 200

        # Check for rupee symbol
        assert '₹' in response.data.decode('utf-8')

        # Check for user data
        assert 'Route Test User' in response.data.decode('utf-8')
        assert 'routetest@example.com' in response.data.decode('utf-8')

        # New user should have 0 expenses
        assert '₹0.00' in response.data.decode('utf-8')
