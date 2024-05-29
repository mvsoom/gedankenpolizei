import logging
import sys
import traceback
from copy import deepcopy
from logging import (
    FileHandler,
    Formatter,
    getLogger,
)
from pathlib import Path
from time import ctime, time

from dateutil.relativedelta import relativedelta

import env

# getLogger("asyncio").setLevel(WARNING)


def epoch_url(epoch):
    """Generate a URL to epochconverter.com for a given epoch time()."""
    # Uses an undocumented feature: http://disq.us/p/2h5flyd
    return f"https://www.epochconverter.com/?q={epoch}"


def human_readable(delta, _attrs=["days", "hours", "minutes", "seconds"]):
    delta.seconds = round(delta.seconds, 3)
    return "".join(
        [
            "%.3g%s" % (getattr(delta, attr), attr[0])
            for attr in _attrs
            if getattr(delta, attr)
        ]
    )


class TimeFilter(logging.Filter):
    def filter(self, record):
        try:
            last = self.last
        except AttributeError:
            last = STARTTIME

        t = time()

        delta = relativedelta(seconds=t - last)

        s = human_readable(delta)

        record.relative = f"[+{s}]({epoch_url(t)})"

        self.last = t
        return True

# Setup the global LOGGER object
STARTTIME = time()
FORMAT = "- %(levelname).1s %(relative)s ```%(message)s```"


def setup_logger():
    logger = getLogger(Path(sys.argv[0]).stem)

    log_file_path = Path(env.LOG_DIR) / env.LOG_FILE
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    h = FileHandler(log_file_path, mode="a")
    h.stream.write(f"# [{ctime(STARTTIME)}]({epoch_url(STARTTIME)})\n")
    h.addFilter(TimeFilter())
    h.setFormatter(Formatter(FORMAT))
    logger.addHandler(h)

    logger.setLevel(env.LOG_LEVEL)

    return logger


LOGGER = setup_logger()

debug = LOGGER.debug
info = LOGGER.info
warning = LOGGER.warning
error = LOGGER.error
critical = LOGGER.critical

# log_public_env_vars()

public_env_vars = {k: v for (k, v) in env._env_vars.items() if not k.startswith("_")}

debug(f"Environment: {public_env_vars}")


def _log_exceptions(type, value, tb):
    for line in traceback.TracebackException(type, value, tb).format(chain=True):
        LOGGER.exception(line, exc_info=False)


sys.excepthook = _log_exceptions


def debug_messages(messages):
    """Mask base64 data in the Claude API messages"""
    messages = deepcopy(messages)
    for message in messages:
        if message["role"] == "user":
            for content in message["content"]:
                if content["type"] == "image":
                    content["source"]["data"] = "<base64>"
    debug(messages)