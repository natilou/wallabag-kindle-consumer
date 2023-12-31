import asyncio
import smtplib
from email.encoders import encode_base64
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

from wallabag_kindle_consumer.config import Configuration
from wallabag_kindle_consumer.logger import logger
from wallabag_kindle_consumer.models import Job, User


class Sender:
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        from_addr: str,
        smtp_server: str,
        smtp_port: int,
        smtp_user: str = "",
        smtp_passwd: str = "",
        smtp_tls: bool = True,
    ):
        self.from_addr = from_addr
        self.loop = loop
        self.host = smtp_server
        self.port = smtp_port
        self.user = smtp_user
        self.passwd = smtp_passwd
        self.encryption_enabled = smtp_tls

    def _send_mail(self, title: str, article: str, format: str, email: str, data: bytes) -> None:
        msg = MIMEMultipart()
        msg["Subject"] = f"Send article '{title}'"
        msg["From"] = self.from_addr
        msg["To"] = email
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid("wallabag-kindle")

        text = "This email has been automatically sent."
        msg.attach(MIMEText(text))

        mobi = MIMEApplication(data)
        encode_base64(mobi)
        mobi.add_header("Content-Disposition", "attachment", filename=f"{title}.{format}")

        msg.attach(mobi)

        smtp = smtplib.SMTP(host=self.host, port=self.port)
        if self.encryption_enabled:
            smtp.starttls()
        if self.user:
            smtp.login(self.user, self.passwd)
        try:
            smtp.sendmail(self.from_addr, [email], msg.as_string())
            smtp.quit()
            logger.info(f"Mail with article {article} in format {format} with title '{title}' sent to {email}")
        except Exception:
            logger.exception("Error sending mail")

    async def send_mail(self, job: Job, data: bytes) -> asyncio.Future[None]:
        return self.loop.run_in_executor(
            None, self._send_mail, job.title, job.article, job.format, job.user.kindle_mail, data
        )

    def _send_warning(self, email: str, config: Configuration) -> None:
        msg = MIMEMultipart()
        msg["Subject"] = "Wallabag-Kindle-Consumer Notice"
        msg["From"] = self.from_addr
        msg["To"] = email
        msg["Date"] = formatdate(localtime=True)

        txt = MIMEText(
            (
                "the Wallabag-Kindle-Consumer for your Wallabag "
                "account on {wallabag} was not able to refresh "
                "the access token. Please go to {url}/update and log "
                "in again to retrieve a new api token."
            ).format(wallabag=config.wallabag_host, url=config.domain)
        )

        msg.attach(txt)

        smtp = smtplib.SMTP(host=self.host, port=self.port)
        if self.encryption_enabled:
            smtp.starttls()
        if self.user:
            smtp.login(self.user, self.passwd)
        try:
            smtp.sendmail(self.from_addr, [email], msg.as_string())
            smtp.quit()
            logger.info(f"Notify email sent to {email}")
        except Exception:
            logger.exception("Error sending notify mail")

    async def send_warning(self, user: User, config: Configuration) -> asyncio.Future[None]:
        return self.loop.run_in_executor(None, self._send_warning, user.email, config)
