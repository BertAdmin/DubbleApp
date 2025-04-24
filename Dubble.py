import numpy as np
import pandas as pd
from datetime import date
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a strong secret key

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('Dubble.db', check_same_thread=False)
cursor = conn.cursor()

# Drop and recreate tables if they don't exist
cursor.execute('DROP TABLE IF EXISTS accounts')
cursor.execute('DROP TABLE IF EXISTS users')

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    balance REAL,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
''')
conn.commit()

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    cursor.execute('SELECT id, username FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    if user_data:
        return User(user_data[0], user_data[1])
    return None

def blow_new_bubble(user_id):
    cursor.execute('INSERT INTO accounts (user_id, balance) VALUES (?, ?)', (user_id, 0.01))
    conn.commit()
    return cursor.lastrowid

def dubble_bubble(account_id, user_id):
    cursor.execute('SELECT balance FROM accounts WHERE id = ? AND user_id = ?', (account_id, user_id))
    row = cursor.fetchone()
    if row:
        balance = row[0] * 2
        cursor.execute('UPDATE accounts SET balance = ? WHERE id = ? AND user_id = ?', (balance, account_id, user_id))
        conn.commit()
        return balance
    return None

def save_and_show_savings_report(user_id):
    cursor.execute('SELECT id, balance FROM accounts WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    savings_report = pd.DataFrame(rows, columns=['ACCOUNT', 'AMOUNT'])
    savings_report['DATE'] = date.today()
    savings_report.to_csv('Dubble.csv', index=False)
    return savings_report.to_dict(orient='records')

def combine_accounts(account_id1, account_id2, user_id):
    cursor.execute('SELECT balance FROM accounts WHERE id = ? AND user_id = ?', (account_id1, user_id))
    row1 = cursor.fetchone()
    cursor.execute('SELECT balance FROM accounts WHERE id = ? AND user_id = ?', (account_id2, user_id))
    row2 = cursor.fetchone()

    if row1 and row2:
        balance1 = row1[0]
        balance2 = row2[0]
        new_balance = balance1 + balance2
        cursor.execute('UPDATE accounts SET balance = ? WHERE id = ? AND user_id = ?', (new_balance, account_id1, user_id))
        cursor.execute('DELETE FROM accounts WHERE id = ? AND user_id = ?', (account_id2, user_id))
        conn.commit()
        return new_balance
    return None

def register_user(username, password):
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def login_user_by_credentials(username, password):
    cursor.execute('SELECT id, username, password FROM users WHERE username = ?', (username,))
    user_data = cursor.fetchone()
    if user_data and user_data[2] == password:
        return User(user_data[0], user_data[1])
    return None

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = login_user_by_credentials(username, password)
        if user:
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if register_user(username, password):
            flash('Registration successful. Please log in.')
            return redirect(url_for('login'))
        else:
            flash('Username already exists')
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/blow_new_bubble', methods=['POST'])
@login_required
def api_blow_new_bubble():
    account_id = blow_new_bubble(current_user.id)
    return jsonify({'id': account_id, 'balance': 0.01})

@app.route('/api/double_bubble', methods=['POST'])
@login_required
def api_double_bubble():
    account_id = request.json.get('account_id')
    balance = dubble_bubble(account_id, current_user.id)
    return jsonify({'balance': balance})

@app.route('/api/save_and_show_savings_report', methods=['GET'])
@login_required
def api_save_and_show_savings_report():
    report = save_and_show_savings_report(current_user.id)
    return jsonify(report)

@app.route('/api/combine_accounts', methods=['POST'])
@login_required
def api_combine_accounts():
    account_id1 = request.json.get('account_id1')
    account_id2 = request.json.get('account_id2')
    new_balance = combine_accounts(account_id1, account_id2, current_user.id)
    return jsonify({'balance': new_balance})

if __name__ == '__main__':
    app.run(debug=True)
