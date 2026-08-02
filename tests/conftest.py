import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('FLASK_SECRET_KEY', 'test-secret-key')

from app import create_app
from app.config import Config
from app.models import db


@pytest.fixture()
def app(tmp_path):
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{tmp_path}/test.db'
        BREEZ_API_KEY = ''
        FLASK_SECRET_KEY = 'test-secret-key'

    application = create_app(TestConfig)
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    monkeypatch.setattr('app.bubble.get_btc_usd', lambda: 100000.0)
    monkeypatch.setattr('app.price.get_btc_usd', lambda: 100000.0)


def csrf_token(client, path):
    html = client.get(path).get_data(as_text=True)
    match = re.search(r'name="csrf-token" content="([^"]+)"', html)
    if not match:
        match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, f'no csrf token found on {path}'
    return match.group(1)


def register(client, username, password):
    token = csrf_token(client, '/register')
    return client.post(
        '/register',
        data={'csrf_token': token, 'username': username, 'password': password},
    )


def login(client, username, password):
    token = csrf_token(client, '/login')
    return client.post(
        '/login',
        data={'csrf_token': token, 'username': username, 'password': password},
    )


def api(client, url, method='GET', body=None):
    token = csrf_token(client, '/')
    resp = client.open(
        url,
        method=method,
        json=body,
        headers={'X-CSRFToken': token},
    )
    return resp
