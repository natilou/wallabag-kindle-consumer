#!/usr/bin/env python3
import asyncio
import datetime

from sqlalchemy.orm import Session, joinedload

from wallabag_kindle_consumer.config import Configuration
from wallabag_kindle_consumer.logger import logger
from wallabag_kindle_consumer.models import Job, User, context_session
from wallabag_kindle_consumer.sender import Sender
from wallabag_kindle_consumer.wallabag import Wallabag


class Consumer:
    def __init__(self, wallabag: Wallabag, cfg: Configuration, sender: Sender):
        self.wallabag = wallabag
        self.sessionmaker = context_session(cfg)
        self.interval = cfg.consume_interval
        self.sender = sender
        self.running = True

        self._wait_fut: asyncio.Future[None] | None = None

    async def fetch_jobs(self, user: User) -> None:
        logger.debug(f"Fetch entries for user {user.name}")
        async for entry in self.wallabag.fetch_entries(user):
            logger.info(f"Schedule job to send entry {entry.id}")
            job = Job(article=entry.id, title=entry.title, format=entry.tag.format)
            user.jobs.append(job)
            await self.wallabag.remove_tag(user, entry)

    async def process_job(self, job: Job, session: Session) -> None:
        logger.info(f"Process export for job {job.article} ({job.format})")
        data = await self.wallabag.export_article(job.user, job.article, job.format)
        if data:
            await self.sender.send_mail(job, data)
        session.delete(job)

    async def _wait_since(self, since: datetime.datetime) -> None:
        now = datetime.datetime.utcnow()
        wait = max(0.0, self.interval - (now - since).total_seconds())

        if not self.running:
            return

        self._wait_fut = asyncio.ensure_future(asyncio.sleep(wait))

        try:
            await self._wait_fut
        except asyncio.CancelledError:
            pass
        finally:
            self._wait_fut = None

    async def consume(self) -> None:
        while self.running:
            start = datetime.datetime.utcnow()

            with self.sessionmaker as session:
                logger.debug("Start consume run")
                fetches = [self.fetch_jobs(user) for user in session.query(User).filter(User.active == True).all()]
                await asyncio.gather(*fetches)
                session.commit()

                jobs = [self.process_job(job, session) for job in session.query(Job).options(joinedload(Job.user))]
                await asyncio.gather(*jobs)
                session.commit()

            await self._wait_since(start)

    def stop(self) -> None:
        self.running = False
        if self._wait_fut is not None:
            self._wait_fut.cancel()
