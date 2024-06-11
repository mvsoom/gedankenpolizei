
import logging
import os
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


def get_log_file_path(module_path, log_dir):
    """Return a log file path for each invoked module in a mirrored directory structure"""
    module_path = os.path.abspath(module_path)
    log_dir = os.path.abspath(log_dir)

    common_path = os.path.commonpath([module_path, log_dir])  # Not available in pathlib
    relative_module_path = os.path.relpath(module_path, common_path)
    new_path = os.path.join(log_dir, relative_module_path)
    new_path = os.path.splitext(new_path)[0] + ".logmd"

    return Path(new_path)


def setup_logger():
    logger = logging.getLogger(Path(sys.argv[0]).stem)
    logger.setLevel(env.LOG_LEVEL)

    log_file_path = get_log_file_path(sys.argv[0], env.LOG_DIR)
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