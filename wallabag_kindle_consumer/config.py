from __future__ import annotations

import dataclasses

from decouple import Config, RepositoryEnv, UndefinedValueError, config

from wallabag_kindle_consumer.logger import logger


@dataclasses.dataclass
class Configuration:
    wallabag_host: str
    db_uri: str
    client_id: str
    client_secret: str
    domain: str
    smtp_from: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_passwd: str
    smtp_tls: bool
    tag: str
    default_format: str
    refresh_grace: int
    consume_interval: int
    interface_host: str
    interface_port: int

    @classmethod
    def build(cls, config_file_path: str | None = None) -> Configuration:
        logger.info("Building configuration")

        cfg = config
        if config_file_path:
            cfg = Config(RepositoryEnv(config_file_path))
        try:
            return cls(
                wallabag_host=cfg("WALLABAG_HOST"),
                db_uri=cfg("DB_URI"),
                client_id=cfg("CLIENT_ID"),
                client_secret=cfg("CLIENT_SECRET"),
                domain=cfg("DOMAIN"),
                smtp_from=cfg("SMTP_FROM"),
                smtp_host=cfg("SMTP_HOST"),
                smtp_port=cfg("SMTP_PORT", cast=int),
                smtp_user=cfg("SMTP_USER"),
                smtp_passwd=cfg("SMTP_PASSWD"),
                smtp_tls=cfg("SMTP_TLS", default=True, cast=bool),
                tag=cfg("TAG", default="kindle"),
                default_format=cfg("DEFAULT_FORMAT", default="epub"),
                refresh_grace=cfg("REFRESH_GRACE", default=120, cast=int),
                consume_interval=cfg("CONSUME_INTERVAL", default=30, cast=int),
                interface_host=cfg("INTERFACE_HOST", default="127.0.0.1"),
                interface_port=cfg("INTERFACE_PORT", default=8080, cast=int),
            )
        except UndefinedValueError:
            logger.exception("Failed to build configuration object")
            raise
