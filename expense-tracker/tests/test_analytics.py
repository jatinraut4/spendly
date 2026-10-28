import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import init_db, create_user


@pytest.fixture
def app():
    """Create Flask app with test configuration."""
    from app import app as flask_app
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
    })
    return flask_app


@pytest.fixture
def client(app, tmp_path):
    """Create a Flask test client with isolated test database."""
    import database.db as db_module
    original_db_path = db_module.DATABASE_PATH
    test_db_path = str(tmp_path / "test_analytics_full.db")
    db_module.DATABASE_PATH = test_db_path

    with app.app_context():
        init_db()

    yield app.test_client()

    db_module.DATABASE_PATH = original_db_path


def test_analytics_redirects_when_logged_out(client):
    """GET /analytics redirects to login when user is not authenticated."""
    response = client.get('/analytics', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_analytics_renders_when_logged_in(client):
    """GET /analytics renders successfully when user is logged in."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1

    # Create dummy user so get_user_by_id succeeds
    with client.application.app_context():
        create_user("Test User", "test@example.com", "password123")

    response = client.get('/analytics')
    assert response.status_code == 200
    assert b'Financial Analytics' in response.data
    assert b'Monthly Spending Trend' in response.data
    assert b'Category Breakdown' in response.data
