from tests.conftest import api, login, register


def _register_and_login(client, username):
    register(client, username, 'secret123')
    assert login(client, username, 'secret123').status_code == 302


def test_blow_confirm_double_flow(client, monkeypatch):
    monkeypatch.setattr('app.lightning.get_cached_mnemonic', lambda user_id: None)
    _register_and_login(client, 'alice')

    resp = api(client, '/api/blow', 'POST')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['mock'] is True
    assert data['amount_sats'] == 10
    assert data['payment_request'].startswith('lnbc')

    resp = api(client, f"/api/confirm/{data['payment_hash']}", 'POST')
    assert resp.status_code == 200

    resp = api(client, '/api/bubbles')
    bubbles = resp.get_json()
    assert len(bubbles) == 1
    assert bubbles[0]['balance_sats'] == 10

    resp = api(client, '/api/double', 'POST', {'bubble_id': data['bubble_id']})
    assert resp.status_code == 200
    double = resp.get_json()
    assert double['amount_sats'] == 20

    resp = api(client, f"/api/confirm/{double['payment_hash']}", 'POST')
    assert resp.status_code == 200

    resp = api(client, '/api/bubbles')
    assert resp.get_json()[0]['balance_sats'] == 30


def test_confirm_ownership_enforced(client, monkeypatch):
    monkeypatch.setattr('app.lightning.get_cached_mnemonic', lambda user_id: None)

    _register_and_login(client, 'alice')
    blow = api(client, '/api/blow', 'POST').get_json()

    client.get('/logout')
    _register_and_login(client, 'mallory')

    resp = api(client, f"/api/confirm/{blow['payment_hash']}", 'POST')
    assert resp.status_code == 400
    assert resp.get_json()['error'] == 'Invoice not found'

    resp = api(client, '/api/bubbles')
    assert resp.get_json() == []


def test_api_requires_csrf_token(client, monkeypatch):
    monkeypatch.setattr('app.lightning.get_cached_mnemonic', lambda user_id: None)
    _register_and_login(client, 'alice')

    resp = client.post('/api/blow')
    assert resp.status_code == 400


def test_withdraw_empties_bubble(client, monkeypatch):
    monkeypatch.setattr('app.lightning.get_cached_mnemonic', lambda user_id: None)
    _register_and_login(client, 'alice')

    blow = api(client, '/api/blow', 'POST').get_json()
    api(client, f"/api/confirm/{blow['payment_hash']}", 'POST')

    resp = api(client, '/api/withdraw', 'POST', {
        'bubble_id': blow['bubble_id'],
        'payment_request': 'lnbc123mock...',
    })
    assert resp.status_code == 200
    assert resp.get_json()['sats_sent'] == 10

    resp = api(client, '/api/bubbles')
    assert resp.get_json()[0]['balance_sats'] == 0


def test_pop_only_when_empty(client, monkeypatch):
    monkeypatch.setattr('app.lightning.get_cached_mnemonic', lambda user_id: None)
    _register_and_login(client, 'alice')

    blow = api(client, '/api/blow', 'POST').get_json()
    api(client, f"/api/confirm/{blow['payment_hash']}", 'POST')

    resp = api(client, f"/api/bubble/{blow['bubble_id']}", 'DELETE')
    assert resp.status_code == 400

    api(client, '/api/withdraw', 'POST', {
        'bubble_id': blow['bubble_id'],
        'payment_request': 'lnbc123mock...',
    })
    resp = api(client, f"/api/bubble/{blow['bubble_id']}", 'DELETE')
    assert resp.status_code == 200
    assert api(client, '/api/bubbles').get_json() == []
