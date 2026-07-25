from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.bubble import (
    blow_bubble,
    double_bubble,
    confirm_payment,
    withdraw_bubble,
    edit_bubble,
    pop_bubble,
    list_bubbles,
    check_pending_invoices,
)

bubble_bp = Blueprint('bubbles', __name__)


@bubble_bp.route('/api/bubbles', methods=['GET'])
@login_required
def api_list_bubbles():
    bubbles = list_bubbles(current_user.id)
    return jsonify(bubbles)


@bubble_bp.route('/api/blow', methods=['POST'])
@login_required
def api_blow():
    result = blow_bubble(current_user.id)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@bubble_bp.route('/api/double', methods=['POST'])
@login_required
def api_double():
    data = request.get_json()
    bubble_id = data.get('bubble_id')
    if not bubble_id:
        return jsonify({'error': 'bubble_id required'}), 400
    result = double_bubble(current_user.id, int(bubble_id))
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@bubble_bp.route('/api/confirm/<payment_hash>', methods=['POST'])
@login_required
def api_confirm(payment_hash):
    result = confirm_payment(payment_hash)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@bubble_bp.route('/api/withdraw', methods=['POST'])
@login_required
def api_withdraw():
    data = request.get_json()
    bubble_id = data.get('bubble_id')
    payment_request = data.get('payment_request')
    if not bubble_id or not payment_request:
        return jsonify({'error': 'bubble_id and payment_request required'}), 400
    result = withdraw_bubble(current_user.id, int(bubble_id), payment_request)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@bubble_bp.route('/api/bubble/<int:bubble_id>', methods=['PATCH'])
@login_required
def api_edit(bubble_id):
    data = request.get_json()
    result = edit_bubble(current_user.id, bubble_id, name=data.get('name'))
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@bubble_bp.route('/api/bubble/<int:bubble_id>', methods=['DELETE'])
@login_required
def api_pop(bubble_id):
    result = pop_bubble(current_user.id, bubble_id)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@bubble_bp.route('/api/check-payments', methods=['POST'])
@login_required
def api_check_payments():
    confirmed = check_pending_invoices(current_user.id)
    return jsonify({'confirmed': confirmed})
