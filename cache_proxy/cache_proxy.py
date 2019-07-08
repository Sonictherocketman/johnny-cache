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


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
@auth.requires_auth
def proxy(path):
    if request.method != 'GET':
        return Response('', 405)

    host = request.headers['host']
    url = f'http://{host}{request.full_path}'

    try:
        check = cache.check(url)
    except Exception:
        pass
    else:
        if check:
            logger.info(f'HIT: {url}')
            return Response(
                check.text,
                200,
                {'X-Cache': 'HIT'},
            )

    headers = {}

    item = cache.get(url)
    if item and not item.is_expired and item.last_modified:
        headers = {
            'If-Modified-Since': formatdate(item.last_modified.timestamp()),
        }

    logger.debug(f'Requesing resource: {url}\n{headers}')
    response = requests.get(url, headers=headers)

    try:
        response.raise_for_status()
    except requests.HTTPError:
        return Response(
            '',
            response.status_code,
            {'X-Cache': 'MISS', **dict(response.headers)}
        )

    if not response.text:
        logger.debug(
            f'URL {url} not modified since {item.last_modified.isoformat()}'
        )
        return Response(
            item.text,
            200,
            {'X-Cache': 'HIT'},
        )

    cache.add(url, response)

    logger.info(f'MISS: {url}.')
    return Response(
        response.text,
        response.status_code,
        {'X-Cache': 'MISS', **dict(response.headers)}
    )


if __name__ == '__main__':
    app.run()
