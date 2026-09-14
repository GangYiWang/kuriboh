# syntax=docker/dockerfile:1.7

FROM python:3.12.13-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app

COPY pyproject.toml ./

RUN --mount=type=cache,id=kuriboh-pip,target=/root/.cache/pip,sharing=locked \
    python -c "import pathlib, subprocess, sys, tomllib; dependencies = tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8'))['project']['dependencies']; subprocess.check_call([sys.executable, '-m', 'pip', 'install', *dependencies])"

COPY app ./app

COPY alembic.ini ./
COPY alembic ./alembic

RUN mkdir -p /app/uploads \
    && chown -R app:app /app

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
