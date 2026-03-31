# -*- encoding:utf-8 -*-
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s[%(levelname)s]%(message)s'
                    , datefmt='%Y-%m-%d %I:%M:%S')
logger = logging.getLogger(__name__)



def log_output(message, level="INFO"):
    if logger == "DEBUG":
        logger.debug(message)
    elif level == "INFO":
        logger.info(message)
    elif level == "WARNING":
        logger.warning(message)
    elif logger == "ERROR":
        logger.error(message)


if "__main__" == __name__:
    log_output("INFO", "test")
