from setup_logging import setup_logger
import threading
import logging

from setup_logging import setup_logger
from background import handwrite_background


def on_starting(server):
    logger = logging.getLogger("background")
    setup_logger(logger)
    t = threading.Thread(target=handwrite_background)
    t.start()
    logger.info("Background Service Thread Started")
