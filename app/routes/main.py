from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.price import get_btc_usd

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    btc_usd = get_btc_usd() or 0
    return render_template('index.html', btc_usd=btc_usd)
