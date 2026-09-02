import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or os.urandom(32).hex()
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///Dubble.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BREEZ_API_KEY = os.environ.get('BREEZ_API_KEY', '')
    BREEZ_NETWORK = os.environ.get('BREEZ_NETWORK', 'mainnet')
    WTF_CSRF_ENABLED = True
    SATS_PER_BTC = 100_000_000
