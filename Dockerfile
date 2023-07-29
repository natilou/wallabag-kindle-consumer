FROM python:3.11-alpine

COPY requirements.txt /tmp
RUN apk add -U --virtual .bdep \
    build-base \
    gcc \
    && \
    pip install -r /tmp/requirements.txt && \
    apk del .bdep

WORKDIR /app
COPY . .

VOLUME /data
EXPOSE 8080

CMD ./service.py --refresher --consumer --interface --env
