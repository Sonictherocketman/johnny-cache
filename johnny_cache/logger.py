import logging
import sys

from . import settings

if settings.LOG_LOCATION == '-':
    logging_config = dict(
        handlers=(logging.StreamHandler(sys.stdout),),
        level=settings.LOG_LEVEL
    )
else:
    logging_config = dict(
        filename=settings.LOG_LOCATION,
        level=settings.LOG_LEVEL
    )

logging.basicConfig(**logging_config)
logger = logging.getLogger('johnnycache')
