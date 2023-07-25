FROM python:3.7-alpine
# TODO: update python version
MAINTAINER Jan Losinski <losinski@wh2.tu-dresden.de>
# TODO: MAINTAINER has been deprecated
# https://docs.docker.com/engine/reference/builder/#maintainer-deprecated

ADD requirements.txt /tmp
RUN apk add -U --virtual .bdep \
    build-base \
    gcc \
    && \
    pip install -r /tmp/requirements.txt && \
    apk del .bdep

ADD . /app
VOLUME /data

WORKDIR /app

EXPOSE 8080

CMD ./service.py --refresher --consumer --interface --env
