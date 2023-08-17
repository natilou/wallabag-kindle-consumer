#!/usr/bin/env python3

import argparse
import asyncio
import logging
import signal

import uvloop

from wallabag_kindle_consumer import models
from wallabag_kindle_consumer.config import Configuration
from wallabag_kindle_consumer.consumer import Consumer
from wallabag_kindle_consumer.interface import App
from wallabag_kindle_consumer.refresher import Refresher
from wallabag_kindle_consumer.sender import Sender
from wallabag_kindle_consumer.wallabag import Wallabag


def parse_args():
    parser = argparse.ArgumentParser(description="Wallabag-Kindle-Consumer")
    parser.add_argument("--cfg", help="Path to config file", required=False)
    parser.add_argument("--refresher", help="Start token refresher", action="store_true")
    parser.add_argument("--interface", help="Start web interface", action="store_true")
    parser.add_argument("--consumer", help="Start article consumer", action="store_true")
    parser.add_argument("--create_db", help="Try to create the db", action="store_true")
    parser.add_argument("--debug", help="Enable debug logging", action="store_true")

    return parser.parse_args()


if __name__ == "__main__":
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    loop = asyncio.get_event_loop()

    args = parse_args()

    logging.basicConfig(level=logging.INFO)
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    config = Configuration.build(config_file_path=args.cfg)

    if args.create_db:
        models.create_db(config)
        logging.info("Database created.")

    on_stop = []

    def _stop():
        for cb in on_stop:
            cb()

        loop.stop()

    loop.add_signal_handler(signal.SIGTERM, _stop)
    loop.add_signal_handler(signal.SIGINT, _stop)

    wallabag = Wallabag(config)
    sender = Sender(
        loop=loop,
        from_addr=config.smtp_from,
        smtp_server=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_user=config.smtp_user,
        smtp_passwd=config.smtp_passwd,
        smtp_tls=config.smtp_tls,
    )

    if args.refresher:
        logging.info("Create Refresher")
        refresher = Refresher(config, wallabag, sender)
        loop.create_task(refresher.refresh())
        on_stop.append(lambda: refresher.stop())

    if args.consumer:
        logging.info("Create Consumer")
        consumer = Consumer(wallabag, config, sender)
        loop.create_task(consumer.consume())
        on_stop.append(lambda: consumer.stop())

    if args.interface:
        logging.info("Create Interface")
        webapp = App(config, wallabag)
        loop.create_task(webapp.register_server())
        on_stop.append(lambda: webapp.stop())

    loop.run_forever()
