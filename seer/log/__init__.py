
import logging
import sys
import traceback
from pathlib import Path
from time import ctime, time

import seer.env as env
from seer.log.format import MarkdownFormatter, epoch_url, markdown_link

STARTTIME = time()

def setup_verbose():
    VERBOSE = 15
    logging.addLevelName(VERBOSE, "VERBOSE")

    def verbose(self, message, *args, **kws):
        if self.isEnabledFor(VERBOSE):
            self._log(VERBOSE, message, args, **kws)

    logging.Logger.verbose = verbose


def setup_logger():
    logger = logging.getLogger(Path(sys.argv[0]).stem)
    logger.setLevel(env.LOG_LEVEL)

    log_file_path = Path(env.LOG_DIR) / env.LOG_FILE
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    h = logging.FileHandler(log_file_path, mode="a")
    h.setFormatter(MarkdownFormatter(STARTTIME))
    logger.addHandler(h)

    # Write out current time and environment variables
    header = markdown_link(ctime(STARTTIME), epoch_url(STARTTIME))
    h.stream.write(f"# {header}\n")

    logger.debug(f"Environment: {env.glob('*')}")

    return logger


def log_exception(type, value, tb):
    trace = "".join(traceback.TracebackException(type, value, tb).format(chain=True))

    LOGGER.exception(trace.strip(), exc_info=False)

    # Pass on to the default exception handler
    sys.__excepthook__(type, value, tb)


# Setup logging and the global LOGGER object
setup_verbose()
LOGGER = setup_logger()

sys.excepthook = log_exception

debug = LOGGER.debug
verbose = LOGGER.verbose
info = LOGGER.info
warning = LOGGER.warning
error = LOGGER.error
critical = LOGGER.critical
