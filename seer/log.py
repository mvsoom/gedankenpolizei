
import sys
import traceback
from logging import FileHandler, Formatter, getLogger
from pathlib import Path
from time import ctime, time

import seer.env as env
from seer.util import TimeFilter, epoch_url, markdown_link

STARTTIME = time()
FORMAT = "- %(levelname).1s %(relative)s ```%(message)s```"


def setup_logger():
    logger = getLogger(Path(sys.argv[0]).stem)
    logger.setLevel(env.LOG_LEVEL)

    log_file_path = Path(env.LOG_DIR) / env.LOG_FILE
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    h = FileHandler(log_file_path, mode="a")
    h.addFilter(TimeFilter(STARTTIME))
    h.setFormatter(Formatter(FORMAT))
    logger.addHandler(h)

    # Write out current time and environment variables
    header = markdown_link(ctime(STARTTIME), epoch_url(STARTTIME))
    h.stream.write(f"# {header}\n")
    public_env_vars = {
        k: v for (k, v) in env._env_vars.items() if not k.startswith("_")
    }
    logger.debug(f"Environment: {public_env_vars}")

    return logger


def log_exception(type, value, tb):
    trace = "".join(traceback.TracebackException(type, value, tb).format(chain=True))
    for line in trace.splitlines():
        LOGGER.exception(line.rstrip(), exc_info=False)

    # Now call the default exception handler
    sys.__excepthook__(type, value, tb)


# Setup the global LOGGER object
LOGGER = setup_logger()

sys.excepthook = log_exception

debug = LOGGER.debug
info = LOGGER.info
warning = LOGGER.warning
error = LOGGER.error
critical = LOGGER.critical
