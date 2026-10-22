# SOMA.i production image.
#
# The image builds the frontend bundle and the Python application, then
# serves both from one origin so that session cookies and CSRF stay
# same-origin.

# --- Frontend build -------------------------------------------------------
FROM node:24.21.0-bookworm-slim AS frontend

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
RUN corepack enable && corepack prepare pnpm@12.11.2 --activate

WORKDIR /build/frontend
# The lockfile is the source of truth, so it is copied before the sources
# so that a dependency-only change does not invalidate the source layer.
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend/ ./
RUN pnpm run build

# --- Python application ---------------------------------------------------
FROM python:3.12.15-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# The locked requirements are copied first so that a source-only change
# does not reinstall the dependency tree.
COPY requirements.txt requirements.lock ./
RUN pip install --require-hashes -r requirements.lock

COPY backend/ ./backend/

# The built bundle is served as the static root.
COPY --from=frontend /build/frontend/dist/ ./frontend/dist/

# The application runs as an unprivileged user.
RUN useradd --create-home --uid 10001 soma \
    && chown -R soma:soma /app
USER soma

ENV DJANGO_SETTINGS_MODULE=soma.settings \
    PYTHONPATH=/app/backend \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health/', timeout=4).status == 200 else 1)"

CMD ["sh", "-c", "python backend/manage.py migrate --noinput && gunicorn soma.wsgi:application --bind 0.0.0.0:${PORT} --workers 2 --access-logfile - --error-logfile -"]
