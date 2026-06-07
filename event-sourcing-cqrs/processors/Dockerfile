FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir sqlalchemy psycopg[binary] redis pydantic

COPY . .

CMD ["python", "risk_processor.py"]
