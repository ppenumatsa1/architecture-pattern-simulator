FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir pydantic sqlalchemy psycopg[binary] redis

COPY shared/python /app/shared/python
COPY microservices/persistence-service /app/microservices/persistence-service

ENV PYTHONPATH=/app
WORKDIR /app/microservices/persistence-service

CMD ["python", "worker.py"]
