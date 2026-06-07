FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn sqlalchemy psycopg[binary]

COPY shared/python /app/shared/python
COPY event-sourcing-cqrs /app/event-sourcing-cqrs

ENV PYTHONPATH=/app
WORKDIR /app/event-sourcing-cqrs/query-api

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
