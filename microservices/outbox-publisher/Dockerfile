FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir sqlalchemy psycopg[binary] redis pydantic

COPY shared/python /app/shared/python
COPY microservices/outbox-publisher /app/microservices/outbox-publisher

ENV PYTHONPATH=/app
WORKDIR /app/microservices/outbox-publisher

CMD ["python", "worker.py"]
