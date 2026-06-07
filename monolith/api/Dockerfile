FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn pydantic sqlalchemy psycopg[binary]

COPY shared/python /app/shared/python
COPY monolith/api /app/monolith/api

ENV PYTHONPATH=/app
WORKDIR /app/monolith/api

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
