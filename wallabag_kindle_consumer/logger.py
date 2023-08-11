import logging

logger = logging.getLogger("wallabag-kindle")
logger.propagate = False

# handlers
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("wallabag_kindle_consumer.log")
file_handler.setLevel(logging.ERROR)

# formatters
console_format = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_format)
file_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_format)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)
