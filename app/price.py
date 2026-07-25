import time
import logging
import requests

logger = logging.getLogger(__name__)

_cache = {'price': None, 'fetched_at': 0}
CACHE_TTL = 60


def get_btc_usd() -> float | None:
    now = time.time()
    if _cache['price'] and (now - _cache['fetched_at']) < CACHE_TTL:
        return _cache['price']

    try:
        resp = requests.get(
            'https://api.coingecko.com/api/v3/simple/price',
            params={'ids': 'bitcoin', 'vs_currencies': 'usd'},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        price = data['bitcoin']['usd']
        _cache['price'] = price
        _cache['fetched_at'] = now
        return price
    except Exception as e:
        logger.warning(f'CoinGecko price fetch failed: {e}')
        return _cache['price']
