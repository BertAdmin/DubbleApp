from datetime import datetime, timezone
from app.models import db, Bubble, Invoice, Wallet
from app.lightning import generate_invoice, pay_invoice, get_balance
from app.price import get_btc_usd


def blow_bubble(user_id: int) -> dict:
    user_wallet = Wallet.query.filter_by(user_id=user_id).first()
    if not user_wallet:
        return {'error': 'No wallet found'}

    price = get_btc_usd()
    sats_per_dollar = 100_000_000 / price if price else 100_000_000
    initial_sats = max(1, int(sats_per_dollar * 0.01))

    inv = generate_invoice(user_id, initial_sats, memo=f'Dubble: blow bubble ({initial_sats} sats)')
    if 'error' in inv:
        return inv

    bubble = Bubble(user_id=user_id, balance_sats=0, balance_usd=0.0)
    db.session.add(bubble)
    db.session.flush()

    invoice = Invoice(
        bubble_id=bubble.id,
        payment_hash=inv['payment_hash'],
        payment_request=inv['payment_request'],
        amount_sats=initial_sats,
        amount_usd=0.01,
        status='pending',
        invoice_type='blow',
    )
    db.session.add(invoice)
    db.session.commit()

    return {
        'bubble_id': bubble.id,
        'payment_request': inv['payment_request'],
        'payment_hash': inv['payment_hash'],
        'amount_sats': initial_sats,
        'amount_usd': 0.01,
        'mock': inv.get('mock', False),
    }


def double_bubble(user_id: int, bubble_id: int) -> dict:
    bubble = Bubble.query.filter_by(id=bubble_id, user_id=user_id).first()
    if not bubble:
        return {'error': 'Bubble not found'}

    double_sats = bubble.balance_sats * 2
    if double_sats < 1:
        return {'error': 'Bubble is empty — blow it first'}

    inv = generate_invoice(user_id, double_sats, memo=f'Dubble: double bubble #{bubble_id}')
    if 'error' in inv:
        return inv

    invoice = Invoice(
        bubble_id=bubble.id,
        payment_hash=inv['payment_hash'],
        payment_request=inv['payment_request'],
        amount_sats=double_sats,
        amount_usd=bubble.balance_usd * 2,
        status='pending',
        invoice_type='double',
    )
    db.session.add(invoice)
    db.session.commit()

    return {
        'bubble_id': bubble.id,
        'payment_request': inv['payment_request'],
        'payment_hash': inv['payment_hash'],
        'amount_sats': double_sats,
        'amount_usd': bubble.balance_usd * 2,
        'mock': inv.get('mock', False),
    }


def confirm_payment(payment_hash: str) -> dict:
    invoice = Invoice.query.filter_by(payment_hash=payment_hash).first()
    if not invoice:
        return {'error': 'Invoice not found'}
    if invoice.status == 'paid':
        return {'error': 'Already paid'}

    invoice.status = 'paid'
    invoice.paid_at = datetime.now(timezone.utc)

    bubble = invoice.bubble
    bubble.balance_sats += invoice.amount_sats
    price = get_btc_usd()
    if price:
        bubble.balance_usd = bubble.balance_sats * (price / 100_000_000)

    wallet = Wallet.query.filter_by(user_id=bubble.user_id).first()
    if wallet:
        wallet.balance_sats = sum(b.balance_sats for b in Bubble.query.filter_by(user_id=bubble.user_id).all())
        if price:
            wallet.balance_usd = wallet.balance_sats * (price / 100_000_000)
        wallet.last_synced_at = datetime.now(timezone.utc)

    db.session.commit()

    return {
        'bubble_id': bubble.id,
        'balance_sats': bubble.balance_sats,
        'balance_usd': bubble.balance_usd,
    }


def withdraw_bubble(user_id: int, bubble_id: int, payment_request: str) -> dict:
    bubble = Bubble.query.filter_by(id=bubble_id, user_id=user_id).first()
    if not bubble:
        return {'error': 'Bubble not found'}
    if bubble.balance_sats <= 0:
        return {'error': 'Bubble is empty'}

    result = pay_invoice(user_id, payment_request)
    if result.get('error'):
        return result

    sats_sent = bubble.balance_sats
    usd_sent = bubble.balance_usd

    bubble.balance_sats = 0
    bubble.balance_usd = 0.0

    price = get_btc_usd()
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    if wallet:
        wallet.balance_sats = sum(b.balance_sats for b in Bubble.query.filter_by(user_id=user_id).all())
        if price:
            wallet.balance_usd = wallet.balance_sats * (price / 100_000_000)
        wallet.last_synced_at = datetime.now(timezone.utc)

    db.session.commit()

    return {
        'bubble_id': bubble.id,
        'sats_sent': sats_sent,
        'usd_sent': usd_sent,
        'mock': result.get('mock', False),
    }


def edit_bubble(user_id: int, bubble_id: int, name: str = None) -> dict:
    bubble = Bubble.query.filter_by(id=bubble_id, user_id=user_id).first()
    if not bubble:
        return {'error': 'Bubble not found'}

    if name is not None:
        bubble.name = name

    db.session.commit()
    return {
        'bubble_id': bubble.id,
        'name': bubble.name,
        'balance_sats': bubble.balance_sats,
        'balance_usd': bubble.balance_usd,
    }


def pop_bubble(user_id: int, bubble_id: int) -> dict:
    bubble = Bubble.query.filter_by(id=bubble_id, user_id=user_id).first()
    if not bubble:
        return {'error': 'Bubble not found'}
    if bubble.balance_sats > 0:
        return {'error': 'Cannot pop a bubble with funds — withdraw first'}

    Invoice.query.filter_by(bubble_id=bubble.id).delete()
    db.session.delete(bubble)
    db.session.commit()

    return {'popped': True, 'bubble_id': bubble_id}


def list_bubbles(user_id: int) -> list[dict]:
    bubbles = Bubble.query.filter_by(user_id=user_id).order_by(Bubble.created_at).all()
    return [
        {
            'id': b.id,
            'name': b.name,
            'balance_sats': b.balance_sats,
            'balance_usd': b.balance_usd,
            'created_at': b.created_at.isoformat() if b.created_at else None,
        }
        for b in bubbles
    ]


def check_pending_invoices(user_id: int) -> list[dict]:
    bubbles = Bubble.query.filter_by(user_id=user_id).all()
    bubble_ids = [b.id for b in bubbles]
    pending = Invoice.query.filter(
        Invoice.bubble_id.in_(bubble_ids),
        Invoice.status == 'pending'
    ).all()

    confirmed = []
    for inv in pending:
        result = confirm_payment(inv.payment_hash)
        if 'error' not in result:
            confirmed.append(result)

    return confirmed
