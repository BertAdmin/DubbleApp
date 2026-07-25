import bcrypt
from flask_login import UserMixin
from app.models import db, User


class LoginUser(UserMixin):
    def __init__(self, user_model):
        self.id = user_model.id
        self.username = user_model.username
        self._user = user_model


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


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
    wallet = Wallet(user_id=user.id)
    db.session.add(wallet)
    db.session.commit()

    return True, 'Registration successful'


def authenticate_user(username: str, password: str) -> User | None:
    user = User.query.filter_by(username=username).first()
    if user and check_password(password, user.password_hash):
        return user
    return None
