from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import register_user, authenticate_user, LoginUser
from app.lightning import derive_mnemonic, get_sdk, disconnect_user
from app.models import User, Wallet

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        success, message = register_user(username, password)
        if success:
            flash(message, 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'error')
    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = authenticate_user(username, password)
        if user:
            login_user(LoginUser(user))

            mnemonic = derive_mnemonic(username, password)
            wallet = Wallet.query.filter_by(user_id=user.id).first()
            if wallet:
                if not wallet.storage_dir:
                    wallet.storage_dir = f'data/wallets/{user.id}'
                    from app.models import db
                    db.session.commit()
                get_sdk(user.id, mnemonic=mnemonic, storage_dir=wallet.storage_dir)

            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    disconnect_user(current_user.id)
    logout_user()
    return redirect(url_for('auth.login'))
