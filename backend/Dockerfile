# Pinned to 3.12, not 3.14 (what local dev happens to be running). 3.14 is too new for several
# dependencies' published wheels (psycopg2-binary, pydantic-core, bcrypt all needed workarounds
# locally) — 3.12 is what's actually stable and widely supported for this stack right now.
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

FROM python:3.12-slim

RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY app app
COPY alembic alembic
COPY alembic.ini .
COPY start.sh .
RUN chmod +x start.sh

RUN mkdir -p /app/uploads && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080
CMD ["./start.sh"]
