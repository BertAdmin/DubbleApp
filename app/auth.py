import base64
import os

import bcrypt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask_login import UserMixin
from mnemonic import Mnemonic
from app.models import db, User

PBKDF2_ITERATIONS = 100_000
NONCE_LEN = 12


class LoginUser(UserMixin):
    def __init__(self, user_model):
        self.id = user_model.id
        self.username = user_model.username
        self._user = user_model


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


def generate_mnemonic() -> str:
    entropy = os.urandom(32)
    return Mnemonic('english').to_mnemonic(entropy)


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode('utf-8'))


def encrypt_mnemonic(mnemonic: str, password: str, salt: bytes | None = None) -> tuple[str, bytes]:
    salt = salt or os.urandom(16)
    key = _derive_key(password, salt)
    nonce = os.urandom(NONCE_LEN)
    ciphertext = AESGCM(key).encrypt(nonce, mnemonic.encode('utf-8'), None)
    payload = base64.b64encode(nonce + ciphertext).decode('ascii')
    return payload, salt


def decrypt_mnemonic(payload: str, salt_hex: str, password: str) -> str:
    salt = bytes.fromhex(salt_hex)
    key = _derive_key(password, salt)
    raw = base64.b64decode(payload)
    nonce, ciphertext = raw[:NONCE_LEN], raw[NONCE_LEN:]
    return AESGCM(key).decrypt(nonce, ciphertext, None).decode('utf-8')


def register_user(username: str, password: str) -> tuple[bool, str]:
    if not username or not password:
        return False, 'Username and password are required'
    if len(username) < 3:
        return False, 'Username must be at least 3 characters'
    if len(password) < 6:
        return False, 'Password must be at least 6 characters'

    existing = User.query.filter_by(username=username).first()
    if existing:
        return False, 'Username already exists'

    user = User(
        username=username,
        password_hash=hash_password(password)
    )
    db.session.add(user)
    db.session.flush()

    from app.models import Wallet
    mnemonic = generate_mnemonic()
    encrypted, salt = encrypt_mnemonic(mnemonic, password)
    wallet = Wallet(
        user_id=user.id,
        storage_dir=f'data/wallets/{user.id}',
        mnemonic_encrypted=encrypted,
        encryption_salt=salt.hex(),
    )
    db.session.add(wallet)
    db.session.commit()

    return True, mnemonic


def authenticate_user(username: str, password: str) -> User | None:
    user = User.query.filter_by(username=username).first()
    if user and check_password(password, user.password_hash):
        return user
    return None


def change_password(user, old_password: str, new_password: str) -> tuple[bool, str]:
    if len(new_password) < 6:
        return False, 'New password must be at least 6 characters'

    if not check_password(old_password, user.password_hash):
        return False, 'Current password is incorrect'

    wallet = user.wallet
    if not wallet or not wallet.mnemonic_encrypted or not wallet.encryption_salt:
        return False, 'This account has no wallet seed — cannot change password'

    try:
        mnemonic = decrypt_mnemonic(
            wallet.mnemonic_encrypted, wallet.encryption_salt, old_password
        )
    except Exception:
        return False, 'Current password could not unlock your wallet'

    encrypted, salt = encrypt_mnemonic(mnemonic, new_password)
    wallet.mnemonic_encrypted = encrypted
    wallet.encryption_salt = salt.hex()
    user.password_hash = hash_password(new_password)
    db.session.commit()

    return True, 'Password changed'
