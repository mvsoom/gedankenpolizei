import sys
import traceback
from copy import deepcopy
from logging import (
    DEBUG,
    WARNING,
    FileHandler,
    Formatter,
    StreamHandler,
    getLogger,
)

from colorlog import ColoredFormatter

getLogger("asyncio").setLevel(WARNING)


LOGGER = getLogger("app")

debug = LOGGER.debug
info = LOGGER.info
warning = LOGGER.warning
error = LOGGER.error
critical = LOGGER.critical


def _log_exceptions(type, value, tb):
    for line in traceback.TracebackException(type, value, tb).format(chain=True):
        LOGGER.exception(line, exc_info=False)


sys.excepthook = _log_exceptions


def config_app_logger(args):
    LOGGER.setLevel(DEBUG)

    # Setup console output
    h = StreamHandler(sys.stderr)
    h.setLevel(args.stderr_level)
    h.setFormatter(ColoredFormatter("%(log_color)s%(message)s%(reset)s"))
    LOGGER.addHandler(h)

    # Setup file handler
    if args.logfile:
        h = FileHandler(args.logfile)
        h.setLevel(args.logfile_level)
        h.setFormatter(Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        LOGGER.addHandler(h)


def debug_messages(messages):
    """Mask base64 data in the Claude API messages"""
    messages = deepcopy(messages)
    for message in messages:
        if message["role"] == "user":
            for content in message["content"]:
                if content["type"] == "image":
                    content["source"]["data"] = "<base64>"
    debug(messages)