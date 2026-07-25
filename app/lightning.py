import os
import asyncio
import hashlib
import logging
from threading import Lock
from flask import current_app

logger = logging.getLogger(__name__)

_server_salt = b'dubble-kdf-salt-v1'
_sdk_instances = {}
_lock = Lock()


def derive_mnemonic(username: str, password: str) -> str:
    from mnemonic import Mnemonic
    entropy = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        (username + ':dubble').encode('utf-8') + _server_salt,
        100_000,
        dklen=16,
    )
    mnemo = Mnemonic('english')
    return mnemo.to_mnemonic(entropy)


def _connect_sdk(mnemonic: str, storage_dir: str):
    from breez_sdk_spark import (
        ConnectRequest,
        Network,
        Seed,
        default_config,
        connect,
    )

    config = default_config(Network.MAINNET)
    config.api_key = current_app.config.get('BREEZ_API_KEY', '')

    seed = Seed.MNEMONIC(mnemonic=mnemonic, passphrase=None)
    os.makedirs(storage_dir, exist_ok=True)

    request = ConnectRequest(config=config, seed=seed, storage_dir=storage_dir)
    return asyncio.run(connect(request))


def get_sdk(user_id: int, mnemonic: str = None, storage_dir: str = None):
    with _lock:
        if user_id in _sdk_instances:
            return _sdk_instances[user_id]

    if mnemonic is None or storage_dir is None:
        return None

    try:
        sdk = _connect_sdk(mnemonic, storage_dir)
    except Exception as e:
        logger.error('SDK connect failed for user %s: %s', user_id, e)
        return None

    with _lock:
        _sdk_instances[user_id] = sdk
    return sdk


def disconnect_user(user_id: int):
    with _lock:
        sdk = _sdk_instances.pop(user_id, None)
    if sdk:
        try:
            asyncio.run(sdk.disconnect())
        except Exception:
            pass


def _mock_invoice(amount_sats: int, memo: str = '') -> dict:
    fake_hash = hashlib.sha256(os.urandom(32)).hexdigest()
    return {
        'mock': True,
        'payment_hash': fake_hash,
        'payment_request': f'lnbc{amount_sats}mock...',
        'amount_sats': amount_sats,
    }


def generate_invoice(user_id: int, amount_sats: int, memo: str = '') -> dict:
    sdk = get_sdk(user_id)
    if sdk is None:
        return _mock_invoice(amount_sats, memo)

    from breez_sdk_spark import ReceivePaymentRequest, ReceivePaymentMethod

    try:
        response = asyncio.run(sdk.receive_payment(
            request=ReceivePaymentRequest(
                payment_method=ReceivePaymentMethod.BOLT11_INVOICE(
                    description=memo or f'Dubble: {amount_sats} sats',
                    amount_sats=amount_sats,
                    expiry_secs=300,
                    payment_hash=None,
                )
            )
        ))

        payment_request = response.payment_request
        payment_hash = hashlib.sha256(payment_request.encode()).hexdigest()

        return {
            'mock': False,
            'payment_hash': payment_hash,
            'payment_request': payment_request,
            'amount_sats': amount_sats,
        }
    except Exception as e:
        logger.error('generate_invoice failed for user %s: %s', user_id, e)
        return {'error': str(e)}


def check_received_payment(user_id: int, payment_request: str) -> dict:
    sdk = get_sdk(user_id)
    if sdk is None:
        return {'mock': True, 'paid': True}

    from breez_sdk_spark import ListPaymentsRequest

    try:
        response = asyncio.run(sdk.list_payments(
            request=ListPaymentsRequest()
        ))
        for payment in response.payments:
            if hasattr(payment, 'payment_request') and payment.payment_request == payment_request:
                return {'mock': False, 'paid': True, 'payment': payment}
        return {'mock': False, 'paid': False}
    except Exception as e:
        logger.error('check_received_payment failed for user %s: %s', user_id, e)
        return {'error': str(e)}


def pay_invoice(user_id: int, payment_request: str) -> dict:
    sdk = get_sdk(user_id)
    if sdk is None:
        return {'mock': True, 'success': True}

    from breez_sdk_spark import PrepareSendPaymentRequest, SendPaymentRequest

    try:
        prepare = asyncio.run(sdk.prepare_send_payment(
            request=PrepareSendPaymentRequest(
                payment_request=payment_request,
                amount=None,
            )
        ))
        response = asyncio.run(sdk.send_payment(
            request=SendPaymentRequest(prepare_response=prepare)
        ))
        return {'mock': False, 'success': True, 'payment': response}
    except Exception as e:
        logger.error('pay_invoice failed for user %s: %s', user_id, e)
        return {'error': str(e)}


def get_balance(user_id: int) -> dict:
    sdk = get_sdk(user_id)
    if sdk is None:
        return {'mock': True, 'balance_sats': 0}

    from breez_sdk_spark import GetInfoRequest

    try:
        info = asyncio.run(sdk.get_info(request=GetInfoRequest(ensure_synced=False)))
        return {
            'mock': False,
            'balance_sats': info.balance_sats,
        }
    except Exception as e:
        logger.error('get_balance failed for user %s: %s', user_id, e)
        return {'error': str(e)}


def list_payments(user_id: int) -> dict:
    sdk = get_sdk(user_id)
    if sdk is None:
        return {'mock': True, 'payments': []}

    from breez_sdk_spark import ListPaymentsRequest

    try:
        response = asyncio.run(sdk.list_payments(request=ListPaymentsRequest()))
        return {'mock': False, 'payments': response.payments}
    except Exception as e:
        logger.error('list_payments failed for user %s: %s', user_id, e)
        return {'error': str(e)}
