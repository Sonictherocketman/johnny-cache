from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from dateutil.parser import parse
import pytz
import requests

from . import settings


logger = logging.getLogger('proxy')


UNCACHED_HEADERS = (
    'Age',
    'Cache-Control',
    'Date',
    'X-Cache',
)


request_cache = {
    # A cache of url:CacheItem pairs.
}


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


# Cache Functions


def check(url):
    item = request_cache.get(url, None)

    if item is None:
        return None

    if not item.is_valid:
        return None

    return item


def get(url):
    return request_cache.get(url, None)


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

    request_cache[url] = CacheItem(
        url=url,
        headers=headers,
        etag=etag,
        expires=parse(expires) if expires else None,
        last_modified=parse(last_modified) if last_modified else None,
        created_at=datetime.now(pytz.utc),
    )

    logger.debug(
        f'Adding: {url}\n'
        f'\tEtag: {etag}\n'
        f'\tExpires: {expires}\n'
        f'\tLast-Modified: {last_modified}\n'
        f'-------------------------------------'
    )
