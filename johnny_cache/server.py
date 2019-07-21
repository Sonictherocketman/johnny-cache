from email.utils import formatdate
import logging

from flask import Flask, request, Response
import requests

from . import settings, auth, cache


app = Flask(__name__)

logging.basicConfig(
    filename=settings.LOG_LOCATION,
    level=settings.LOG_LEVEL
)
logger = logging.getLogger('proxy')


NO_STORE = 'no-store'


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
@auth.requires_auth
def proxy(path):
    if request.method != 'GET':
        return Response('', 405)

    host = request.headers['host']
    url = f'https://{host}{request.full_path}'

    cache_control = request.headers.get('cache-control', '').lower()

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

    if cache_control != NO_STORE:
        item = cache.get(url)
        if item and not item.is_expired and item.etag:
            headers['If-None-Match'] = item.etag
        elif item and not item.is_expired and item.last_modified:
            headers['If-Modified-Since'] = formatdate(item.last_modified.timestamp())

    logger.debug(f'Requesing resource: {url}\n{headers}')
    try:
        response = requests.get(url, headers=headers, stream=True)
    except Exception:
        try:
            # Try again with plain-text HTTP
            response = requests.get(
                url.replace('https://', 'http://'),
                headers=headers,
                stream=True,
            )
        except Exception as e:
            return Response(f'Error contacting {url}.\n{e}', 500)

    logger.info(f'MISS: {url}.')
    try:
        response.raise_for_status()
    except requests.HTTPError:
        return Response(
            response.raw.read(),
            response.status_code,
            {'X-Cache': 'MISS', **dict(response.headers)}
        )

    if cache_control != NO_STORE:
        cache.add(url, response)

    return Response(
        response.raw.read(),
        response.status_code,
        {'X-Cache': 'MISS', **dict(response.headers)}
    )


if __name__ == '__main__':
    app.run()
