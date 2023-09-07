# mock wallabag server for testing purposes

FROM python:3.11-alpine

WORKDIR /app

RUN pip install fastapi
RUN pip install "uvicorn[standard]" && pip install ipdb

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
