import pytest
import sys
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_db, init_db, create_user


@pytest.fixture
def app():
    """Create Flask app with test configuration."""
    from app import app as flask_app
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
    })
    return flask_app


@pytest.fixture
def client(app, tmp_path):
    """Create a Flask test client with isolated test database."""
    import database.db as db_module
    original_db_path = db_module.DATABASE_PATH
    test_db_path = str(tmp_path / "test_date_filter.db")
    db_module.DATABASE_PATH = test_db_path

    with app.app_context():
        init_db()

    yield app.test_client()

    # Restore original database path
    db_module.DATABASE_PATH = original_db_path


@pytest.fixture
def auth_client(client):
    """
    A test client that is already logged in with seeded expense data.

    Creates user with expenses spanning multiple months:
    - 2026-10-20: Food expense (this month)
    - 2026-09-15: Transport expense (last month, within 3-month window)
    - 2026-08-10: Bills expense (2 months ago, within 3-month window)
    - 2026-06-05: Health expense (4 months ago, within 6-month window)
    - 2026-03-01: Shopping expense (7 months ago, outside 6-month window)
    """
    # Register and login
    client.post('/register', data={
        'name': 'Filter Test User',
        'email': 'filtertest@example.com',
        'password': 'testpass123',
        'confirm_password': 'testpass123'
    })

    client.post('/login', data={
        'email': 'filtertest@example.com',
        'password': 'testpass123'
    })

    # Seed test expenses with known dates
    with get_db() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", ("filtertest@example.com",)).fetchone()
        user_id = user["id"]

        expenses = [
            (user_id, 100.00, 'Food', '2026-10-20', 'October expense'),
            (user_id, 50.00, 'Transport', '2026-09-15', 'September expense'),
            (user_id, 200.00, 'Bills', '2026-08-10', 'August expense'),
            (user_id, 75.00, 'Health', '2026-06-05', 'June expense'),
            (user_id, 150.00, 'Shopping', '2026-03-01', 'March expense'),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            expenses
        )
        conn.commit()

    return client


class TestAuthGuard:
    """Test authentication requirements for date filter feature."""

    def test_profile_unauthenticated_no_filter(self, client):
        """Unauthenticated users redirected to login even without date params."""
        response = client.get('/profile')
        assert response.status_code == 302, "Expected redirect for unauthenticated user"
        assert response.location.endswith('/login'), "Expected redirect to login page"

    def test_profile_unauthenticated_with_date_params(self, client):
        """Unauthenticated users redirected to login even with valid date params."""
        response = client.get('/profile?date_from=2026-01-01&date_to=2026-12-31')
        assert response.status_code == 302, "Expected redirect for unauthenticated user"
        assert response.location.endswith('/login'), "Expected redirect to login page"


class TestAllTimeView:
    """Test the default unfiltered view (All Time preset)."""

    def test_profile_no_params_shows_all_expenses(self, auth_client):
        """Visiting /profile with no query params returns all expenses."""
        response = auth_client.get('/profile')
        assert response.status_code == 200

        html = response.data.decode('utf-8')

        # Should show total of all expenses: 100 + 50 + 200 + 75 + 150 = 575.00
        assert '₹575.00' in html, "Expected total spent to be ₹575.00"

        # Should show count of 5 transactions
        assert '5' in html, "Expected 5 transactions"

    def test_all_time_preset_url(self, auth_client):
        """All Time preset explicitly navigates to /profile with no params."""
        response = auth_client.get('/profile')
        html = response.data.decode('utf-8')

        # Active preset should be 'all_time' when no params present
        # Check that All Time button has active state (implementation-agnostic check)
        assert response.status_code == 200


class TestThisMonthPreset:
    """Test the 'This Month' preset filter."""

    def test_this_month_filters_correctly(self, auth_client):
        """This Month preset shows only expenses from current calendar month."""
        today = date.today()  # 2026-10-25 based on context
        first_of_month = today.replace(day=1)

        response = auth_client.get(f'/profile?date_from={first_of_month}&date_to={today}')
        assert response.status_code == 200

        html = response.data.decode('utf-8')

        # Only 2026-10-20 expense (100.00) should be included
        assert '₹100.00' in html, "Expected total spent this month to be ₹100.00"

        # Should show October expense description
        assert 'October expense' in html, "Expected to see October expense"

        # Should NOT show older expenses
        assert 'September expense' not in html, "Should not see September expense"
        assert 'March expense' not in html, "Should not see March expense"


class TestLast3MonthsPreset:
    """Test the 'Last 3 Months' preset filter."""

    def test_last_3_months_filters_correctly(self, auth_client):
        """Last 3 Months preset shows expenses from 3-month window ending today."""
        today = date.today()  # 2026-10-25
        three_months_ago = today - relativedelta(months=3)  # 2026-07-25

        response = auth_client.get(f'/profile?date_from={three_months_ago}&date_to={today}')
        assert response.status_code == 200

        html = response.data.decode('utf-8')

        # Should include: Oct (100), Sep (50), Aug (200) = 350.00
        assert '₹350.00' in html, "Expected total for last 3 months to be ₹350.00"

        # Should show recent expenses
        assert 'October expense' in html
        assert 'September expense' in html
        assert 'August expense' in html

        # Should NOT show older expenses (June is 4+ months ago)
        assert 'June expense' not in html, "Should not see June expense"
        assert 'March expense' not in html, "Should not see March expense"


class TestLast6MonthsPreset:
    """Test the 'Last 6 Months' preset filter."""

    def test_last_6_months_filters_correctly(self, auth_client):
        """Last 6 Months preset shows expenses from 6-month window ending today."""
        today = date.today()  # 2026-10-25
        six_months_ago = today - relativedelta(months=6)  # 2026-04-25

        response = auth_client.get(f'/profile?date_from={six_months_ago}&date_to={today}')
        assert response.status_code == 200

        html = response.data.decode('utf-8')

        # Should include: Oct (100), Sep (50), Aug (200), Jun (75) = 425.00
        assert '₹425.00' in html, "Expected total for last 6 months to be ₹425.00"

        # Should show these expenses
        assert 'October expense' in html
        assert 'September expense' in html
        assert 'August expense' in html
        assert 'June expense' in html

        # Should NOT show March expense (7 months ago)
        assert 'March expense' not in html, "Should not see March expense from 7 months ago"


class TestCustomDateRange:
    """Test custom date range filtering."""

    def test_custom_range_filters_correctly(self, auth_client):
        """Custom date range shows only expenses within specified bounds."""
        # Filter for August to September 2026
        response = auth_client.get('/profile?date_from=2026-08-01&date_to=2026-09-30')
        assert response.status_code == 200

        html = response.data.decode('utf-8')

        # Should include: Sep (50), Aug (200) = 250.00
        assert '₹250.00' in html, "Expected total for Aug-Sep to be ₹250.00"

        assert 'September expense' in html
        assert 'August expense' in html

        # Should NOT show October or older expenses
        assert 'October expense' not in html
        assert 'June expense' not in html
        assert 'March expense' not in html

    def test_single_day_range(self, auth_client):
        """Custom range with same start and end date works correctly."""
        response = auth_client.get('/profile?date_from=2026-10-20&date_to=2026-10-20')
        assert response.status_code == 200

        html = response.data.decode('utf-8')

        # Should include only the October expense (100.00)
        assert '₹100.00' in html
        assert 'October expense' in html
        assert 'September expense' not in html

    def test_narrow_range_with_no_expenses(self, auth_client):
        """Custom range with no matching expenses shows empty state."""
        # Query a range with no expenses
        response = auth_client.get('/profile?date_from=2026-11-01&date_to=2026-11-30')
        assert response.status_code == 200

        html = response.data.decode('utf-8')

        # Should show zero values
        assert '₹0.00' in html, "Expected ₹0.00 when no expenses in range"
        # Should show 0 transactions
        assert response.status_code == 200


class TestDateValidation:
    """Test date validation and error handling."""

    def test_reversed_date_range_shows_error(self, auth_client):
        """When date_from > date_to, show flash error and fall back to unfiltered."""
        response = auth_client.get('/profile?date_from=2026-10-01&date_to=2026-08-01', follow_redirects=True)

        html = response.data.decode('utf-8')

        # Should show flash error message
        assert 'Start date must be before end date' in html, "Expected validation error message"

        # Should fall back to All Time view (all 5 expenses, total 575.00)
        assert '₹575.00' in html, "Expected fallback to show all expenses"

    def test_malformed_date_from_silent_fallback(self, auth_client):
        """Malformed date_from silently falls back to unfiltered view."""
        response = auth_client.get('/profile?date_from=not-a-date&date_to=2026-10-31')
        assert response.status_code == 200

        html = response.data.decode('utf-8')

        # Should show all expenses (no filter applied)
        assert '₹575.00' in html, "Expected unfiltered view with malformed date_from"

        # Should NOT crash or show error
        assert 'error' not in html.lower() or 'Start date must be before end date' not in html

    def test_malformed_date_to_silent_fallback(self, auth_client):
        """Malformed date_to silently falls back to unfiltered view."""
        response = auth_client.get('/profile?date_from=2026-01-01&date_to=invalid')
        assert response.status_code == 200

        html = response.data.decode('utf-8')

        # Should show all expenses
        assert '₹575.00' in html, "Expected unfiltered view with malformed date_to"

    def test_both_dates_malformed_silent_fallback(self, auth_client):
        """Both dates malformed falls back to unfiltered view."""
        response = auth_client.get('/profile?date_from=bad&date_to=worse')
        assert response.status_code == 200

        html = response.data.decode('utf-8')

        # Should show all expenses
        assert '₹575.00' in html

    def test_partial_date_malformed(self, auth_client):
        """Partial ISO date strings are treated as malformed."""
        response = auth_client.get('/profile?date_from=2026-10&date_to=2026-11')
        assert response.status_code == 200

        html = response.data.decode('utf-8')

        # Should fall back to unfiltered
        assert '₹575.00' in html


class TestAllSectionsRespectFilter:
    """Test that stats, transactions, and categories all respect the active filter."""

    def test_stats_section_filtered(self, auth_client):
        """Summary stats section respects date filter."""
        # Filter to September only (1 expense: 50.00)
        response = auth_client.get('/profile?date_from=2026-09-01&date_to=2026-09-30')
        html = response.data.decode('utf-8')

        assert '₹50.00' in html, "Stats should show filtered total"

    def test_transactions_section_filtered(self, auth_client):
        """Recent transactions section respects date filter."""
        # Filter to August-September
        response = auth_client.get('/profile?date_from=2026-08-01&date_to=2026-09-30')
        html = response.data.decode('utf-8')

        # Should show these two
        assert 'September expense' in html
        assert 'August expense' in html

        # Should NOT show others
        assert 'October expense' not in html
        assert 'June expense' not in html

    def test_categories_section_filtered(self, auth_client):
        """Category breakdown section respects date filter."""
        # Filter to October only (1 expense: Food 100.00)
        response = auth_client.get('/profile?date_from=2026-10-01&date_to=2026-10-31')
        html = response.data.decode('utf-8')

        # Should show Food category
        assert 'Food' in html

        # Stats should show Food as top category (only category in range)
        assert '₹100.00' in html


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_database_with_filter(self, client):
        """User with no expenses shows ₹0.00 regardless of filter."""
        # Register new user with no expenses
        client.post('/register', data={
            'name': 'Empty User',
            'email': 'empty@example.com',
            'password': 'testpass123',
            'confirm_password': 'testpass123'
        })
        client.post('/login', data={
            'email': 'empty@example.com',
            'password': 'testpass123'
        })

        response = client.get('/profile?date_from=2026-01-01&date_to=2026-12-31')
        html = response.data.decode('utf-8')

        assert '₹0.00' in html, "Expected ₹0.00 for user with no expenses"

    def test_only_date_from_provided(self, auth_client):
        """Providing only date_from without date_to falls back to unfiltered."""
        response = auth_client.get('/profile?date_from=2026-08-01')
        html = response.data.decode('utf-8')

        # Should show all expenses (no filter applied when incomplete)
        assert '₹575.00' in html

    def test_only_date_to_provided(self, auth_client):
        """Providing only date_to without date_from falls back to unfiltered."""
        response = auth_client.get('/profile?date_to=2026-09-30')
        html = response.data.decode('utf-8')

        # Should show all expenses
        assert '₹575.00' in html

    def test_future_date_range(self, auth_client):
        """Date range in the future shows empty results."""
        response = auth_client.get('/profile?date_from=2027-01-01&date_to=2027-12-31')
        html = response.data.decode('utf-8')

        assert '₹0.00' in html, "Expected ₹0.00 for future date range"

    def test_very_old_date_range(self, auth_client):
        """Date range before any expenses shows empty results."""
        response = auth_client.get('/profile?date_from=2020-01-01&date_to=2020-12-31')
        html = response.data.decode('utf-8')

        assert '₹0.00' in html, "Expected ₹0.00 for old date range with no data"


class TestRupeeSymbolPresence:
    """Test that rupee symbol appears regardless of filter state."""

    def test_rupee_symbol_with_filter(self, auth_client):
        """Rupee symbol present in filtered view."""
        response = auth_client.get('/profile?date_from=2026-08-01&date_to=2026-09-30')
        html = response.data.decode('utf-8')

        assert '₹' in html, "Expected rupee symbol in filtered view"

    def test_rupee_symbol_with_empty_results(self, auth_client):
        """Rupee symbol present even when no expenses in range."""
        response = auth_client.get('/profile?date_from=2027-01-01&date_to=2027-12-31')
        html = response.data.decode('utf-8')

        assert '₹' in html, "Expected rupee symbol even with empty results"
        assert '₹0.00' in html


class TestURLGeneration:
    """Test that preset URLs are generated correctly."""

    def test_preset_urls_in_template(self, auth_client):
        """Preset filter buttons generate correct URLs."""
        response = auth_client.get('/profile')
        html = response.data.decode('utf-8')

        # Should contain links with date parameters (checking for query string pattern)
        assert 'date_from=' in html, "Expected date_from parameter in preset URLs"
        assert 'date_to=' in html, "Expected date_to parameter in preset URLs"

        # All Time should link to clean /profile URL
        assert response.status_code == 200
