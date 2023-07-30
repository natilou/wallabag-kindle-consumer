ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-alpine AS builder

RUN apk add -U \
      build-base \
      gcc \
    && pip install pipenv==2023.7.23

WORKDIR /usr/src
COPY Pipfile Pipfile.lock ./

RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy


FROM python:${PYTHON_VERSION}-alpine

WORKDIR /app

COPY --from=builder /usr/src/.venv/ /usr/src/.venv/
ENV PATH="/usr/src/.venv/bin/:${PATH}"

COPY . .

VOLUME /data
EXPOSE 8080

CMD ./service.py --refresher --consumer --interface --env
