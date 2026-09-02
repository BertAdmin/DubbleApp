from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import urlsplit
from app.auth import register_user, authenticate_user, LoginUser, decrypt_mnemonic
from app.lightning import cache_mnemonic, drop_mnemonic

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        success, result = register_user(username, password)
        if success:
            return render_template('backup_mnemonic.html', mnemonic=result)
        else:
            flash(result, 'error')
    return render_template('register.html')


@auth_bp.route('/register/acknowledge', methods=['POST'])
def register_acknowledge():
    flash('Registration complete — please log in with your password.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = authenticate_user(username, password)
        if user:
            wallet = user.wallet
            if wallet and wallet.mnemonic_encrypted and wallet.encryption_salt:
                try:
                    mnemonic = decrypt_mnemonic(wallet.mnemonic_encrypted, wallet.encryption_salt, password)
                except Exception:
                    flash('Could not unlock your wallet. Double-check your password.', 'error')
                    return render_template('login.html')
                cache_mnemonic(user.id, mnemonic)
            elif not wallet or not wallet.mnemonic_encrypted:
                flash('This account has no wallet seed. Please re-register.', 'error')
                return render_template('login.html')

            login_user(LoginUser(user))

            next_page = request.args.get('next')
            if next_page and urlsplit(next_page).netloc == '':
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    drop_mnemonic(current_user.id)
    logout_user()
    return redirect(url_for('auth.login'))
