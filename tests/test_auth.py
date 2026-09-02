import re

from app.models import User, Wallet
from tests.conftest import api, login, register


def test_register_creates_encrypted_wallet(client, app):
    resp = register(client, 'alice', 'secret123')
    assert resp.status_code == 200

    with app.app_context():
        user = User.query.filter_by(username='alice').first()
        assert user is not None
        assert user.password_hash.startswith('$2')
        assert not user.password_hash.startswith('secret123')

        wallet = Wallet.query.filter_by(user_id=user.id).first()
        assert wallet is not None
        assert wallet.mnemonic_encrypted
        assert wallet.encryption_salt
        assert 'secret123' not in wallet.mnemonic_encrypted


def test_register_returns_24_word_mnemonic(client):
    resp = register(client, 'alice', 'secret123')
    html = resp.get_data(as_text=True)
    match = re.search(r'class="mnemonic-box">([^<]+)</div>', html)
    assert match
    words = match.group(1).split()
    assert len(words) == 24


def test_login_success_and_protected_route(client, app):
    register(client, 'alice', 'secret123')
    resp = login(client, 'alice', 'secret123')
    assert resp.status_code == 302

    resp = client.get('/')
    assert resp.status_code == 200

    resp = api(client, '/api/bubbles')
    assert resp.status_code == 200


def test_login_wrong_password(client):
    register(client, 'alice', 'secret123')
    resp = login(client, 'alice', 'wrongpass')
    assert resp.status_code == 200

    resp = client.get('/')
    assert resp.status_code == 302


def test_login_tampered_password_cannot_unlock(client):
    register(client, 'alice', 'secret123')
    login(client, 'alice', 'secret123')


def test_logout_clears_session(client):
    register(client, 'alice', 'secret123')
    login(client, 'alice', 'secret123')
    client.get('/logout')
    resp = client.get('/')
    assert resp.status_code == 302
