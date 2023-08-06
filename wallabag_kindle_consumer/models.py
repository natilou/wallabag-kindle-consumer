import datetime

from sqlalchemy import Enum, ForeignKey, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    ...


class User(Base):
    __tablename__ = "user"

    name: Mapped[str] = mapped_column(primary_key=True)
    token: Mapped[str | None]
    auth_token: Mapped[str]
    refresh_token: Mapped[str]
    token_valid: Mapped[datetime.datetime]
    last_check: Mapped[datetime.datetime | None]
    email: Mapped[str]
    kindle_mail: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True)

    jobs: Mapped[list["Job"]] = relationship(back_populates="user")


class Job(Base):
    __tablename__ = "job"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    article: Mapped[int]
    title: Mapped[str]
    user_name: Mapped[int | None] = mapped_column(ForeignKey("user.name"))
    format = mapped_column(Enum("pdf", "mobi", "epub"))

    user: Mapped["User"] = relationship(back_populates="jobs")


class ContextSession:
    def __init__(self, session_maker):
        self.session_maker = session_maker

    def __enter__(self):
        self.session = self.session_maker()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()


def context_session(config):
    return ContextSession(session_maker(config))


def session_maker(config):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=create_engine(config.db_uri))
    return Session


def create_db(config):
    engine = create_engine(config.db_uri)
    Base.metadata.create_all(engine)


def re_create_db(config):
    engine = create_engine(config.db_uri)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
