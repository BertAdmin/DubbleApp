import re

from app.models import User, Wallet
from tests.conftest import api, csrf_token, login, register


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


def test_mnemonic_not_in_client_cookie(client, app):
    register(client, 'alice', 'secret123')
    token = csrf_token(client, '/login')
    resp = client.post(
        '/login',
        data={'csrf_token': token, 'username': 'alice', 'password': 'secret123'},
    )
    assert resp.status_code == 302

    cookie_header = resp.headers.get('Set-Cookie', '')
    assert 'alice' not in cookie_header
    with app.app_context():
        wallet = Wallet.query.filter_by(user_id=User.query.filter_by(username='alice').first().id).first()
        assert wallet and wallet.mnemonic_encrypted
        assert wallet.mnemonic_encrypted not in cookie_header


def _change_password(client, old, new, confirm):
    token = csrf_token(client, '/change-password')
    assert token, 'no csrf token on change-password page'
    return client.post(
        '/change-password',
        data={
            'csrf_token': token,
            'old_password': old,
            'new_password': new,
            'confirm_password': confirm,
        },
    )


def test_change_password_success_rekeys_wallet(client, app):
    register(client, 'alice', 'secret123')
    login(client, 'alice', 'secret123')
    with app.app_context():
        old_hash = User.query.filter_by(username='alice').first().password_hash

    resp = _change_password(client, 'secret123', 'newpass456', 'newpass456')
    assert resp.status_code == 302

    with app.app_context():
        user = User.query.filter_by(username='alice').first()
        wallet = Wallet.query.filter_by(user_id=user.id).first()
        assert user.password_hash != old_hash
        assert wallet.mnemonic_encrypted
        from app.auth import decrypt_mnemonic
        mnemonic = decrypt_mnemonic(wallet.mnemonic_encrypted, wallet.encryption_salt, 'newpass456')
        assert len(mnemonic.split()) == 24


def test_change_password_old_password_fails_after_change(client):
    register(client, 'alice', 'secret123')
    login(client, 'alice', 'secret123')
    _change_password(client, 'secret123', 'newpass456', 'newpass456')

    client.get('/logout')
    resp = login(client, 'alice', 'secret123')
    assert resp.status_code == 200
    assert client.get('/').status_code == 302

    resp = login(client, 'alice', 'newpass456')
    assert resp.status_code == 302


def test_change_password_wrong_current_rejected(client):
    register(client, 'alice', 'secret123')
    login(client, 'alice', 'secret123')
    resp = _change_password(client, 'wrongpass', 'newpass456', 'newpass456')
    assert resp.status_code == 200


def test_change_password_mismatch_confirmation(client):
    register(client, 'alice', 'secret123')
    login(client, 'alice', 'secret123')
    resp = _change_password(client, 'secret123', 'newpass456', 'different789')
    assert resp.status_code == 200
    assert login(client, 'alice', 'secret123').status_code == 302
