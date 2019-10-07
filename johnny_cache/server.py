from email.utils import formatdate

from flask import Flask, request, Response
import requests

from . import auth, cache
from .logger import logger


app = Flask(__name__)


NO_STORE = 'no-store'


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
@auth.requires_auth
def proxy(path):
    if request.method != 'GET':
        return Response('', 405)

    # The protocol can come from another proxy, or from a custom X-Proto header.
    # If nothing is present, default to HTTP.
    proto = request.headers.get(
        'x-forwarded-proto',
        request.headers.get('x-proto', 'http')
    )

    host = request.headers['host']
    url = f'{proto}://{host}{request.full_path}'

    cache_control = request.headers.get('cache-control', '').lower()
    if cache_control:
        logger.debug(f'Using client provided cache policy: {cache_control}')

    if cache_control != NO_STORE:
        try:
            check = cache.check(url)
        except Exception as e:
            logger.error(f'Exception in cache check {e}')
            pass
        else:
            if check:
                logger.info(f'HIT: {url}')
                return Response('', 304)

    headers = {}

    user_agent = request.headers.get('user-agent', None)
    if user_agent:
        logger.debug(f'Using client provided user-agent: {user_agent}')
        headers['User-Agent'] = user_agent

    if cache_control != NO_STORE:
        item = cache.get(url)
        if item and not item.is_expired and item.etag:
            headers['If-None-Match'] = item.etag
        elif item and not item.is_expired and item.last_modified:
            headers['If-Modified-Since'] = formatdate(item.last_modified.timestamp())

    logger.info(f'MISS: {url}.')
    with requests.get(url, headers=headers) as response:
        if response.ok and cache_control != NO_STORE:
            cache.add(url, response)

        response_headers = {}
        if response.headers.get('content-type', None):
            response_headers['Content-Type'] = response.headers['content-type']

        return (
            response.content,
            response.status_code,
            {'X-Cache': 'MISS', **response_headers},
        )


if __name__ == '__main__':
    app.run()
