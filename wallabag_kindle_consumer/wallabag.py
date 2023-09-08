from collections import namedtuple
from collections.abc import AsyncIterator
from datetime import datetime, timedelta

import aiohttp

from wallabag_kindle_consumer.config import Configuration
from wallabag_kindle_consumer.logger import logger
from wallabag_kindle_consumer.models import User


class Article:
    def __init__(self, id, tags, title, tag, **kwargs):
        self.id = id
        self.tags = tags
        self.title = title
        self.tag = tag

    def tag_id(self) -> int:
        for t in self.tags:
            if t["label"] == self.tag.tag:
                return t["id"]

        return -1


Tag = namedtuple("Tag", ["tag", "format"])


def make_tags(tag: str, default_format: str) -> tuple[Tag, ...]:
    return (
        Tag(tag=f"{tag}", format=default_format),
        Tag(tag=f"{tag}-epub", format="epub"),
        Tag(tag=f"{tag}-mobi", format="mobi"),
        Tag(tag=f"{tag}-pdf", format="pdf"),
    )


class Wallabag:
    def __init__(self, config: Configuration):
        self.config = config
        self.tag = config.tag
        self.tags = make_tags(tag=self.tag, default_format=config.default_format)

    async def get_token(self, user: User, passwd: str) -> bool:
        params = {
            "grant_type": "password",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "username": user.name,
            "password": passwd,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self._url("/oauth/v2/token"), json=params) as resp:
                if resp.status != 200:
                    logger.error(f"Cannot get token for user {user.name}", exc_info=True)
                    return False
                data = await resp.json()
                user.auth_token = data["access_token"]
                user.refresh_token = data["refresh_token"]
                user.token_valid = datetime.utcnow() + timedelta(seconds=data["expires_in"])
                logger.info(f"Got new token for {user.name}")

                return True

    async def refresh_token(self, user: User) -> bool:
        params = {
            "grant_type": "refresh_token",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": user.refresh_token,
            "username": user.name,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self._url("/oauth/v2/token"), json=params) as resp:
                if resp.status != 200:
                    logger.error(f"Cannot refresh token for user {user.name}", exc_info=True)
                    return False
                data = await resp.json()
                user.auth_token = data["access_token"]
                user.refresh_token = data["refresh_token"]
                user.token_valid = datetime.utcnow() + timedelta(seconds=data["expires_in"])

                return True

    def _api_params(self, user: User, params: dict[str, str] | None = None) -> dict[str, str]:
        if params is None:
            params = {}

        params["access_token"] = user.auth_token
        return params

    def _url(self, url: str) -> str:
        return self.config.wallabag_host + url

    async def fetch_entries(self, user: User) -> AsyncIterator[Article]:
        if user.auth_token is None:
            logger.error(f"No auth token for {user.name}", exc_info=True)
            return
        async with aiohttp.ClientSession() as session:
            for tag in self.tags:
                params = self._api_params(user, {"tags": tag.tag})
                async with session.get(self._url("/api/entries.json"), params=params) as resp:
                    if resp.status != 200:
                        logger.warning(f"Could not get entries of tag {tag.tag} for user {user.name}")
                        return

                    data = await resp.json()
                    if data["pages"] == 1:
                        user.last_check = datetime.utcnow()

                    articles = data["_embedded"]["items"]
                    for article in articles:
                        yield Article(tag=tag, **article)

    async def remove_tag(self, user: User, article: Article) -> None:
        params = self._api_params(user)
        tag = article.tag_id()
        url = self._url(f"/api/entries/{article.id}/tags/{tag}.json")

        async with aiohttp.ClientSession() as session:
            async with session.delete(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning(
                        f"Cannot remove tag {article.tag.tag} from entry '{article.title}' of user {user.name}",
                    )
                    return
                logger.info(
                    f"Removed tag {article.tag.tag} from article '{article.title}' of user {user.name}",
                )

    async def export_article(self, user: User, article_id: int, format: str) -> bytes | None:
        params = self._api_params(user)
        url = self._url(f"/api/entries/{article_id}/export.{format}")

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.error(
                        f"Cannot export article {article_id} of user {user.name} in format {format}", exc_info=True
                    )
                    return None

                return await resp.read()
