from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    wallet = db.relationship('Wallet', backref='user', uselist=False)
    bubbles = db.relationship('Bubble', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'


class Wallet(db.Model):
    __tablename__ = 'wallets'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    storage_dir = db.Column(db.String(256), nullable=True)
    mnemonic_encrypted = db.Column(db.Text, nullable=True)
    encryption_salt = db.Column(db.String(32), nullable=True)
    balance_sats = db.Column(db.Integer, default=0)
    balance_usd = db.Column(db.Float, default=0.0)
    last_synced_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Wallet user={self.user_id} sats={self.balance_sats}>'


class Bubble(db.Model):
    __tablename__ = 'bubbles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), default='')
    balance_sats = db.Column(db.Integer, default=0)
    balance_usd = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    invoices = db.relationship('Invoice', backref='bubble', lazy=True)

    def __repr__(self):
        return f'<Bubble {self.id} sats={self.balance_sats}>'


class Invoice(db.Model):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bubble_id = db.Column(db.Integer, db.ForeignKey('bubbles.id'), nullable=False)
    payment_hash = db.Column(db.String(64), unique=True, nullable=False)
    payment_request = db.Column(db.Text, nullable=False)
    amount_sats = db.Column(db.Integer, nullable=False)
    amount_usd = db.Column(db.Float)
    status = db.Column(db.String(20), default='pending')
    invoice_type = db.Column(db.String(20), default='blow')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    paid_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Invoice {self.payment_hash[:8]}... status={self.status}>'
