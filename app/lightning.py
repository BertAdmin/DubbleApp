import asyncio
import hashlib
import logging
import os
import time

from flask import current_app, session

logger = logging.getLogger(__name__)

MNEMONIC_TTL_SECS = 3600
_SESSION_KEY = '_dubble_mnemonic'
_SESSION_AT = '_dubble_mnemonic_at'


def cache_mnemonic(user_id: int, mnemonic: str):
    session[_SESSION_KEY] = mnemonic
    session[_SESSION_AT] = time.time()


def get_cached_mnemonic(user_id: int) -> str | None:
    mnemonic = session.get(_SESSION_KEY)
    cached_at = session.get(_SESSION_AT)
    if not mnemonic or not cached_at:
        return None
    if time.time() - cached_at > MNEMONIC_TTL_SECS:
        drop_mnemonic(user_id)
        return None
    return mnemonic


def drop_mnemonic(user_id: int):
    session.pop(_SESSION_KEY, None)
    session.pop(_SESSION_AT, None)


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _storage_dir(user_id: int) -> str:
    from app.models import Wallet
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    if wallet and wallet.storage_dir:
        return wallet.storage_dir
    return f'data/wallets/{user_id}'


async def _build_sdk(user_id: int):
    from breez_sdk_spark import (
        Network,
        SdkBuilder,
        Seed,
        SyncWalletRequest,
        default_server_config,
    )

    mnemonic = get_cached_mnemonic(user_id)
    if not mnemonic:
        return None

    config = default_server_config(Network.MAINNET)
    config.api_key = current_app.config.get('BREEZ_API_KEY', '')

    seed = Seed.MNEMONIC(mnemonic=mnemonic, passphrase=None)
    storage_dir = _storage_dir(user_id)
    os.makedirs(storage_dir, exist_ok=True)

    builder = SdkBuilder(config=config, seed=seed)
    await builder.with_default_storage(storage_dir=storage_dir)
    sdk = await builder.build()
    await sdk.sync_wallet(request=SyncWalletRequest())
    return sdk


def _mock_invoice(amount_sats: int, memo: str = '') -> dict:
    fake_hash = hashlib.sha256(os.urandom(32)).hexdigest()
    return {
        'mock': True,
        'payment_hash': fake_hash,
        'payment_request': f'lnbc{amount_sats}mock...',
        'amount_sats': amount_sats,
    }


def generate_invoice(user_id: int, amount_sats: int, memo: str = '') -> dict:
    if get_cached_mnemonic(user_id) is None:
        return _mock_invoice(amount_sats, memo)

    async def op():
        sdk = await _build_sdk(user_id)
        if sdk is None:
            return _mock_invoice(amount_sats, memo)

        from breez_sdk_spark import ReceivePaymentMethod, ReceivePaymentRequest

        try:
            response = await sdk.receive_payment(
                request=ReceivePaymentRequest(
                    payment_method=ReceivePaymentMethod.BOLT11_INVOICE(
                        description=memo or f'Dubble: {amount_sats} sats',
                        amount_sats=amount_sats,
                        expiry_secs=300,
                        payment_hash=None,
                    )
                )
            )

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
        finally:
            try:
                await sdk.disconnect()
            except Exception:
                pass

    return _run(op())


def check_received_payment(user_id: int, payment_request: str) -> dict:
    if get_cached_mnemonic(user_id) is None:
        return {'mock': True, 'paid': True}

    async def op():
        sdk = await _build_sdk(user_id)
        if sdk is None:
            return {'mock': True, 'paid': True}

        from breez_sdk_spark import ListPaymentsRequest

        try:
            response = await sdk.list_payments(request=ListPaymentsRequest())
            for payment in response.payments:
                if hasattr(payment, 'payment_request') and payment.payment_request == payment_request:
                    return {'mock': False, 'paid': True, 'payment': payment}
            return {'mock': False, 'paid': False}
        except Exception as e:
            logger.error('check_received_payment failed for user %s: %s', user_id, e)
            return {'error': str(e)}
        finally:
            try:
                await sdk.disconnect()
            except Exception:
                pass

    return _run(op())


def pay_invoice(user_id: int, payment_request: str) -> dict:
    if get_cached_mnemonic(user_id) is None:
        return {'mock': True, 'success': True}

    async def op():
        sdk = await _build_sdk(user_id)
        if sdk is None:
            return {'mock': True, 'success': True}

        from breez_sdk_spark import PrepareSendPaymentRequest, SendPaymentRequest

        try:
            prepare = await sdk.prepare_send_payment(
                request=PrepareSendPaymentRequest(
                    payment_request=payment_request,
                    amount=None,
                )
            )
            response = await sdk.send_payment(
                request=SendPaymentRequest(prepare_response=prepare)
            )
            return {'mock': False, 'success': True, 'payment': response}
        except Exception as e:
            logger.error('pay_invoice failed for user %s: %s', user_id, e)
            return {'error': str(e)}
        finally:
            try:
                await sdk.disconnect()
            except Exception:
                pass

    return _run(op())


def get_balance(user_id: int) -> dict:
    if get_cached_mnemonic(user_id) is None:
        return {'mock': True, 'balance_sats': 0}

    async def op():
        sdk = await _build_sdk(user_id)
        if sdk is None:
            return {'mock': True, 'balance_sats': 0}

        from breez_sdk_spark import GetInfoRequest

        try:
            info = await sdk.get_info(request=GetInfoRequest(ensure_synced=False))
            return {
                'mock': False,
                'balance_sats': info.balance_sats,
            }
        except Exception as e:
            logger.error('get_balance failed for user %s: %s', user_id, e)
            return {'error': str(e)}
        finally:
            try:
                await sdk.disconnect()
            except Exception:
                pass

    return _run(op())


def list_payments(user_id: int) -> dict:
    if get_cached_mnemonic(user_id) is None:
        return {'mock': True, 'payments': []}

    async def op():
        sdk = await _build_sdk(user_id)
        if sdk is None:
            return {'mock': True, 'payments': []}

        from breez_sdk_spark import ListPaymentsRequest

        try:
            response = await sdk.list_payments(request=ListPaymentsRequest())
            return {'mock': False, 'payments': response.payments}
        except Exception as e:
            logger.error('list_payments failed for user %s: %s', user_id, e)
            return {'error': str(e)}
        finally:
            try:
                await sdk.disconnect()
            except Exception:
                pass

    return _run(op())
