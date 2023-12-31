import asyncio
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from wallabag_kindle_consumer.config import Configuration
from wallabag_kindle_consumer.logger import logger
from wallabag_kindle_consumer.models import User, context_session
from wallabag_kindle_consumer.sender import Sender
from wallabag_kindle_consumer.wallabag import Wallabag


class Refresher:
    def __init__(self, config: Configuration, wallabag: Wallabag, sender: Sender):
        self.sessionmaker = context_session(config)
        self.wallabag = wallabag
        self.grace = config.refresh_grace
        self.sender = sender
        self.config = config

        self._running = True
        self._wait_fut: asyncio.Future[None] | None = None

    def _wait_time(self, session: Session) -> float:
        next = session.query(func.min(User.token_valid).label("min")).filter(User.active == True).first()
        if next is None or next.min is None:
            return 3
        delta = next.min - datetime.utcnow()
        if delta < timedelta(seconds=self.grace):
            return 0

        calculated = delta - timedelta(seconds=self.grace)
        return calculated.total_seconds()

    async def refresh(self) -> None:
        while self._running:
            with self.sessionmaker as session:
                self._wait_fut = asyncio.ensure_future(asyncio.sleep(self._wait_time(session)))
                try:
                    await self._wait_fut
                except asyncio.CancelledError:
                    continue
                finally:
                    self._wait_fut = None

                ts = datetime.utcnow() + timedelta(seconds=self.grace)
                refreshes = [
                    self._refresh_user(user)
                    for user in session.query(User).filter(User.active == True).filter(User.token_valid < ts).all()
                ]
                await asyncio.gather(*refreshes)

                session.commit()

    async def _refresh_user(self, user: User) -> None:
        logger.info(f"Refresh token for {user.name}")
        if not await self.wallabag.refresh_token(user):
            await self.sender.send_warning(user, self.config)
            user.active = False

    def stop(self) -> None:
        self._running = False
        if self._wait_fut is not None:
            self._wait_fut.cancel()
