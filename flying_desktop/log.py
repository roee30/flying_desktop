"""
Logging utilities
"""
import logging
from pathlib import Path

from appdirs import user_log_dir
from . import APP_NAME


LOG_FILE = Path(user_log_dir(), "flying_desktop.log")


LOG_FORMAT = logging.Formatter(
    " - ".join(f"%({x})s" for x in ["asctime", "levelname", "name", "message"]),
)


def logging_setup():
    """
    Attach handlers to the application's root logger
    """
    main_log = logging.getLogger(APP_NAME)
    main_log.setLevel(logging.DEBUG)
    LOG_FILE.parent.mkdir(exist_ok=True, parents=True)
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    for handler in console_handler, file_handler:
        handler.setFormatter(LOG_FORMAT)
        main_log.addHandler(handler)
