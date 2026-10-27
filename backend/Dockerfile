# Backend image for LOCAL DEVELOPMENT / TESTING only — not hardened for production.
# Build context is the repository root (see docker-compose.yml) so Poetry can
# read pyproject.toml / poetry.lock which live at the repo root.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.5 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# Build tooling and libs some wheels/browsers may need. Playwright's
# `--with-deps` step below pulls the rest of the browser system libraries.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN pip install "poetry==${POETRY_VERSION}"

# Install Python deps first for better layer caching.
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-interaction --no-ansi

# Browser for scrapy-playwright / playwright. Comment out to slim the image
# if you don't need the crawlers locally.
# RUN playwright install --with-deps chromium

# App code (overridden by the bind mount in docker-compose for live reload).
WORKDIR /app/backend
COPY backend/ ./

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
