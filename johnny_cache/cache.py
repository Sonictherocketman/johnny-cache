from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os.path

from dateutil.parser import parse
import pytz
import redis
from redis.lock import LockError
import requests

from . import settings
from .logger import logger


UNCACHED_HEADERS = (
    'Age',
    'Cache-Control',
    'Date',
    'X-Cache',
)


def get_cache():
    if settings.REDIS_URL:
        logger.info('Using Redis Cache.')
        return RedisCache(settings.REDIS_URL)

    logger.info('Using Local Cache.')
    return PersistedCache(
        os.path.join(settings.CACHE_LOCATION, settings.CACHE_NAME)
    )


class PersistedCache(object):

    store = {}

    def __init__(self, cache_location):
        self.cache_location = cache_location
        try:
            self.store.update(self.load(cache_location))
        except IOError:
            logger.warn('No existing cache detected. Will create one.')
        except Exception:
            logger.error('Could not load cache. Removing and recreating.')
            self.save()
        finally:
            logger.info(f'Cache prepopulated with {len(self.store.keys())} items.')

    def get(self, key):
        return self.store.get(key, None)

    def set(self, key, value):
        self.store[key] = value
        try:
            self.save()
        except Exception:
            logger.error('Could not load cache. Dumping store and regenerating.')
            self.store = {}
            self.save()

    def save(self):
        with open(self.cache_location, 'w+') as f:
            json.dump({
                key: cache_item.encode()
                for key, cache_item in self.store.items()
            }, f)

    def load(self, cache_location):
        with open(cache_location, 'r+') as f:
            return {
                key: CacheItem.decode(value)
                for key, value in json.load(f).items()
            }


class RedisCache(object):

    def __init__(self, url):
        self.ttl = (
            settings.MAX_CACHE_SECONDS
            if settings.MAX_CACHE_SECONDS > 0
            else None
        )
        self.client = redis.Redis.from_url(url)
        logger.info(f'Connected to redis: {url}')

    def get(self, key):
        value = self.client.get(key)
        if not value:
            return None
        return CacheItem.decode(json.loads(value))

    def set(self, key, value):
        value = json.dumps(value.encode())
        try:
            with self.client.lock(f'lock__{key}', blocking_timeout=6, timeout=2):
                self.client.set(key, value, ex=self.ttl)
        except LockError as e:
            logger.error(f'Failed to aquire lock for key {key}\n{e}')

        return None


@dataclass
class CacheItem:
    """ A record in the cache. """
    url: str
    headers: dict
    etag: str
    expires: datetime
    last_modified: datetime
    created_at: datetime

    @property
    def is_expired(self):
        if settings.MAX_CACHE_SECONDS == 0:
            return False

        expires = (
            self.created_at + timedelta(seconds=settings.MAX_CACHE_SECONDS)
        )
        return expires < datetime.now(pytz.utc)

    @property
    def is_valid(self):
        logger.debug(
            f'Using: {self.url}\n'
            f'\tEtag: {self.etag}\n'
            f'\tExpires: {self.expires}\n'
            f'\tLast-Modified: {self.last_modified}\n'
            f'-------------------------------------'
        )

        if not self.expires and not self.last_modified and not self.etag:
            logger.debug('No cache information.')
            return False

        if self.etag == '-1':
            logger.debug(f'Forcing uncached version due to Etag: {self.etag}')
            return False

        if self.is_expired:
            logger.debug('CacheItem has expired.')
            return False

        if self.expires and self.expires > datetime.now(pytz.utc):
            logger.debug('Using cached version due to Expires.')
            return True

        logger.debug(f'>>> HEAD {self.url}')
        head_check = requests.head(self.url)

        try:
            head_check.raise_for_status()
        except requests.HTTPError:
            return False

        etag = head_check.headers.get('etag', None)
        logger.debug(f'Trying ETag... {etag}')
        if etag and etag == self.etag:
            return True

        last_modified = head_check.headers.get('last-modified', None)
        logger.debug(f'Trying Last-Modified... {last_modified}')
        if (
            last_modified
            and self.last_modified
            and parse(last_modified) <= self.last_modified
        ):
            return True

        return False

    def encode(self):
        return [
            self.url,
            self.headers,
            self.etag,
            self.expires.isoformat() if self.expires else None,
            self.last_modified.isoformat() if self.last_modified else None,
            self.created_at.isoformat(),
        ]

    @classmethod
    def decode(cls, value):
        url, headers, etag, expires_str, last_modified_str, created_at_str = value

        return CacheItem(
            url=url,
            headers=headers,
            etag=etag,
            expires=parse(expires_str) if expires_str else None,
            last_modified=parse(last_modified_str) if last_modified_str else None,
            created_at=parse(created_at_str)
        )


# Global Cache


request_cache = get_cache()


# Cache Functions


def check(url):
    item = request_cache.get(url)

    if item is None:
        return None

    if not item.is_valid:
        return None

    return item


def get(url):
    return request_cache.get(url)


def add(url, response):
    expires = response.headers.get('expires')
    last_modified = response.headers.get('last-modified')
    etag = response.headers.get('etag')
    if etag:
        etag = (
            etag
            .replace('W/', '')  # replace weak comparison marker
            .replace('"', '')   # replace quotes
        )

    headers = {
        key: value
        for key, value in dict(response.headers).items()
        if key not in UNCACHED_HEADERS
    }

    request_cache.set(url, CacheItem(
        url=url,
        headers=headers,
        etag=etag,
        expires=parse(expires) if expires else None,
        last_modified=parse(last_modified) if last_modified else None,
        created_at=datetime.now(pytz.utc),
    ))

    logger.debug(
        f'Adding: {url}\n'
        f'\tEtag: {etag}\n'
        f'\tExpires: {expires}\n'
        f'\tLast-Modified: {last_modified}\n'
        f'-------------------------------------'
    )
