import os
import logging


LOG_LEVEL = getattr(logging, os.environ.get('LOG_LEVEL', 'info').upper())
LOG_LOCATION = os.environ.get('LOG_LOCATION', './proxy.log')


# Authentication Settings


if os.environ.get('HTTP_USERS', False):
    HTTP_USERS = [
        entry for entry in os.environ.get('HTTP_USERS').split(',')
    ]
else:
    HTTP_USERS = []

# Cache Settings

MAX_CACHE_SECONDS = int(os.environ.get('MAX_CACHE_SECONDS', 0))