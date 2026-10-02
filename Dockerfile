FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY app ./app
COPY web ./web
COPY migrations ./migrations

RUN pip install --no-cache-dir .
RUN alembic heads | awk '{print $1}' > /app/ALEMBIC_HEAD

ENV APP_ENV=production
EXPOSE 8000

CMD ["sh", "-c", "python -m app.core.migracao && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --limit-concurrency ${UVICORN_LIMIT_CONCURRENCY:-200} --timeout-keep-alive 5"]
