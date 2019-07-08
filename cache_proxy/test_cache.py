import pytest


# Fixtures


@pytest.fixture
def uncached_cache_url(request):
    from uuid import uuid4
    return f'http://uncached_cache_url.com/{uuid4()}?query=param&param=two'


@pytest.fixture
def uncached_cache_item(request, uncached_cache_url):
    from . import cache
    from datetime import datetime

    return cache.CacheItem(
        url=uncached_cache_url,
        text='',
        etag=None,
        expires=None,
        last_modified=None,
        created_at=datetime.now()
    )


@pytest.fixture
def expired_cache_url(request):
    from uuid import uuid4
    return f'http://expired_cache_url.com/{uuid4()}/path?query=param&param=two'


@pytest.fixture
def expired_cache_item(request, expired_cache_url):
    from . import cache
    from datetime import datetime, timedelta

    return cache.CacheItem(
        url=expired_cache_url,
        text='',
        etag=None,
        expires=datetime.now() + timedelta(hours=1),
        last_modified=None,
        created_at=datetime.now()
    )


@pytest.fixture
def etag_cache_url(request):
    from uuid import uuid4
    return f'http://etag_cache_url.com/{uuid4()}/path?query=param&param=two'


@pytest.fixture
def etag_cache_item(request, etag_cache_url):
    from . import cache
    from datetime import datetime

    return cache.CacheItem(
        url=etag_cache_url,
        text='',
        etag='abcd-efgh-ijkl-mnop',
        expires=None,
        last_modified=None,
        created_at=datetime.now()
    )


@pytest.fixture
def last_modified_cache_url(request):
    from uuid import uuid4
    return f'http://last_modified_cache_url.com/{uuid4()}'


@pytest.fixture
def last_modified_cache_item(request, last_modified_cache_url):
    from . import cache
    from datetime import datetime, timedelta

    return cache.CacheItem(
        url=last_modified_cache_url,
        text='',
        etag=None,
        expires=None,
        last_modified=datetime.now() - timedelta(days=3),
        created_at=datetime.now()
    )


@pytest.fixture
def preloaded_cache(
    request,
    uncached_cache_url,
    uncached_cache_item,
    expired_cache_url,
    expired_cache_item,
    etag_cache_url,
    etag_cache_item,
    last_modified_cache_url,
    last_modified_cache_item
):
    return {
        uncached_cache_url: uncached_cache_item,
        expired_cache_url: expired_cache_item,
        etag_cache_url: etag_cache_item,
        last_modified_cache_url: last_modified_cache_item,
    }


@pytest.fixture
def response(request):
    return {}


# Mocks

class MockResponse:

    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)

    @property
    def headers(self):
        return {
            'last-modified': getattr(self, 'last_modified', None),
            'etag': getattr(self, 'etag', None),
        }

    def raise_for_status(self):
        pass


# Tests


def test_uncached(uncached_cache_url, preloaded_cache, monkeypatch):
    from . import cache
    monkeypatch.setattr(cache, 'request_cache', preloaded_cache)

    entry = cache.check(uncached_cache_url)
    assert entry is None


def test_expired(expired_cache_url, preloaded_cache, monkeypatch):
    from . import cache
    monkeypatch.setattr(cache, 'request_cache', preloaded_cache)

    entry = cache.check(expired_cache_url)
    assert entry is not None


def test_etag(etag_cache_url, preloaded_cache, monkeypatch):
    from . import cache
    import requests
    monkeypatch.setattr(cache, 'request_cache', preloaded_cache)
    monkeypatch.setattr(requests, 'head', lambda _: MockResponse(
        etag=preloaded_cache[etag_cache_url].etag
    ))

    entry = cache.check(etag_cache_url)
    assert entry is not None


def test_last_modified(last_modified_cache_url, preloaded_cache, monkeypatch):
    from . import cache
    import requests
    monkeypatch.setattr(cache, 'request_cache', preloaded_cache)

    cache_item = preloaded_cache[last_modified_cache_url]
    monkeypatch.setattr(requests, 'head', lambda _: MockResponse(
        last_modified=cache_item.last_modified.isoformat()
    ))

    entry = cache.check(last_modified_cache_url)
    assert entry is not None
