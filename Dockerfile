FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY app ./app
COPY web ./web
COPY migrations ./migrations

RUN pip install --no-cache-dir .

ENV APP_ENV=production
EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
