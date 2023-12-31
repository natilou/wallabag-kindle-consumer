import asyncio
import os
from collections.abc import Mapping
from typing import Any

import aiohttp_jinja2
import jinja2
from aiohttp import web
from email_validator import EmailNotValidError, ValidatedEmail, validate_email

from wallabag_kindle_consumer.logger import logger

from . import config, models, wallabag


class Validator:
    def __init__(self, loop: asyncio.AbstractEventLoop, data: Mapping[str, Any]):
        self.loop = loop
        self.data = data
        self.errors: dict[str, str] = {}
        self.username: str = ""
        self.password: str = ""
        self.kindle_email: str = ""
        self.notify_email: str = ""

    async def validate_credentials(self) -> bool:
        errors = {}
        if "username" not in self.data or 0 == len(self.data["username"]):
            errors["username"] = "Username not given or empty"
        else:
            self.username = self.data["username"]

        if "password" not in self.data or 0 == len(self.data["password"]):
            errors["password"] = "Password not given or empty"
        else:
            self.password = self.data["password"]

        self.errors.update(errors)
        return 0 == len(errors)

    async def _validate_email(self, address: str) -> str:
        val: ValidatedEmail = await self.loop.run_in_executor(None, validate_email, address)
        return val.normalized

    async def validate_emails(self) -> bool:
        errors = {}
        if "kindleEmail" not in self.data or 0 == len(self.data["kindleEmail"]):
            errors["kindleEmail"] = "Kindle email address not given or empty"
        else:
            try:
                kindleEmail = await self._validate_email(self.data["kindleEmail"])
                if kindleEmail.endswith("@kindle.com") or kindleEmail.endswith("@free.kindle.com"):
                    self.kindle_email = kindleEmail
                else:
                    errors["kindleEmail"] = "Given Kindle email does not end with @kindle.com or @free.kindle.com"
            except EmailNotValidError:
                errors["kindleEmail"] = "Kindle email is not a valid email address"

        if "notifyEmail" not in self.data or 0 == len(self.data["notifyEmail"]):
            errors["notifyEmail"] = "Notification email not given or empty"
        else:
            try:
                self.notify_email = await self._validate_email(self.data["notifyEmail"])
            except EmailNotValidError:
                errors["notifyEmail"] = "Notification email is not a valid email address"

        self.errors.update(errors)
        return 0 == len(errors)

    @property
    def success(self) -> bool:
        return 0 == len(self.errors)


class ViewBase(web.View):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._errors: dict[str, str] = {}
        self._data: Mapping[str, Any] = {}
        self._messages: list[str] = []

    @property
    def _cfg(self) -> config.Configuration:
        return self.request.app["config"]

    @property
    def _wallabag(self) -> wallabag.Wallabag:
        return self.request.app["wallabag"]

    def _template(self, vars: dict[str, Any]) -> dict[str, Any]:
        vars.update(
            {
                "errors": self._errors,
                "data": self._data,
                "messages": self._messages,
                "wallabag_host": self._cfg.wallabag_host,
                "tags": [t.tag for t in wallabag.make_tags(tag=self._cfg.tag, default_format=self._cfg.default_format)],
            }
        )
        return vars

    def _add_errors(self, errors: dict[str, str]) -> None:
        self._errors.update(errors)

    def _set_data(self, data: Mapping[str, Any]) -> None:
        self._data = data

    def _add_message(self, msg: str) -> None:
        self._messages.append(msg)

    @property
    def _session(self) -> models.ContextSession:
        return self.request.app["session_maker"]


class IndexView(ViewBase):
    @aiohttp_jinja2.template("index.html")
    async def get(self) -> dict[str, Any]:
        return self._template({})

    @aiohttp_jinja2.template("index.html")
    async def post(self) -> dict[str, Any]:
        data = await self.request.post()
        self._set_data(data)

        validator = Validator(self.request.app.loop, data)

        await asyncio.gather(validator.validate_emails(), validator.validate_credentials())
        self._add_errors(validator.errors)

        if validator.success:
            user = models.User(
                name=validator.username, kindle_mail=validator.kindle_email, email=validator.notify_email
            )

            with self._session as session:
                if session.query(models.User.name).filter(models.User.name == validator.username).count() != 0:
                    self._add_errors({"user": "User is already registered"})
                elif not await self._wallabag.get_token(user, validator.password):
                    self._add_errors({"auth": "Cannot authenticate at wallabag server to get a token"})
                else:
                    session.add(user)
                    session.commit()
                    self._add_message(f"User {validator.username} successfully registered")
                    self._set_data({})
                    logger.info(f"User {validator.username} registered")

        return self._template({})


class ReLoginView(ViewBase):
    @aiohttp_jinja2.template("relogin.html")
    async def get(self) -> dict[str, Any]:
        return self._template({"action": "update", "description": "Refresh"})

    @aiohttp_jinja2.template("relogin.html")
    async def post(self) -> dict[str, Any]:
        data = await self.request.post()
        self._set_data(data)

        validator = Validator(self.request.app.loop, data)
        await validator.validate_credentials()
        self._add_errors(validator.errors)

        if validator.success:
            with self._session as session:
                user = session.query(models.User).filter(models.User.name == validator.username).first()
                if user is None:
                    self._add_errors({"user": "User not registered"})
                else:
                    if await self._wallabag.get_token(user, validator.password):
                        user.active = True
                        session.commit()
                        self._add_message(f"User {validator.username} successfully updated.")
                        logger.info(f"User {user} successfully updated.")
                    else:
                        self._add_errors({"auth": "Authentication against wallabag server failed"})

        return self._template({"action": "update", "description": "Refresh"})


class DeleteView(ViewBase):
    @aiohttp_jinja2.template("relogin.html")
    async def get(self) -> dict[str, Any]:
        return self._template({"action": "delete", "description": "Delete"})

    @aiohttp_jinja2.template("relogin.html")
    async def post(self) -> dict[str, Any]:
        data = await self.request.post()
        self._set_data(data)

        validator = Validator(self.request.app.loop, data)
        await validator.validate_credentials()
        self._add_errors(validator.errors)

        if validator.success:
            with self._session as session:
                user = session.query(models.User).filter(models.User.name == validator.username).first()
                if user is None:
                    self._add_errors({"user": "User not registered"})
                else:
                    if await self._wallabag.get_token(user, validator.password):
                        session.delete(user)
                        session.commit()
                        self._add_message(f"User {validator.username} successfully deleted.")
                        logger.info(f"User {user} successfully deleted.")
                    else:
                        self._add_errors({"auth": "Authentication against wallabag server failed"})

        return self._template({"action": "delete", "description": "Delete"})


class App:
    def __init__(self, config: config.Configuration, wallabag: wallabag.Wallabag):
        self.config = config
        self.wallabag = wallabag
        self.app = web.Application()
        self.site: web.TCPSite | None = None

        self.setup_app()
        self.setup_routes()

    def setup_app(self) -> None:
        self.app["config"] = self.config
        self.app["wallabag"] = self.wallabag
        self.app["session_maker"] = models.context_session(self.config)
        aiohttp_jinja2.setup(self.app, loader=jinja2.PackageLoader("wallabag_kindle_consumer", "templates"))

        self.app["static_root_url"] = "/static"

    def setup_routes(self) -> None:
        self.app.router.add_static("/static/", path=os.path.join(os.path.dirname(__file__), "static"), name="static")
        self.app.router.add_view("/", IndexView)
        self.app.router.add_view("/delete", DeleteView)
        self.app.router.add_view("/update", ReLoginView)

    def run(self) -> None:
        web.run_app(self.app, host=self.config.interface_host, port=self.config.interface_port)

    async def register_server(self) -> None:
        app_runner = web.AppRunner(self.app, access_log=logger)
        await app_runner.setup()
        self.site = web.TCPSite(app_runner, self.config.interface_host, self.config.interface_port)
        await self.site.start()

    def stop(self) -> None:
        if self.site is not None:
            asyncio.get_event_loop().create_task(self.site.stop())
