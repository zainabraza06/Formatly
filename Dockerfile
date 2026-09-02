# Formatly, as one image: the built page served by the API that answers it.
#
# One origin, so there is no CORS to configure and no second deployment to keep
# in step. LibreOffice is here because Exact view and the PDF download go
# through it; without it those two lose their fidelity and everything else
# works, so a smaller image is a fair trade if you do not need them (see the
# note by the apt-get line).

# ── the page ────────────────────────────────────────────────────────────────
FROM node:20-slim AS frontend

WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
# No environment file: the page then calls the origin it was served from, which
# is this same container. A development .env naming 127.0.0.1 would otherwise
# be compiled in, and the deployed page would call the reader's own machine.
# Set VITE_API_URL here only if the API lives somewhere else.
RUN rm -f .env .env.* && npm run build


# ── the API, and the page with it ───────────────────────────────────────────
FROM python:3.12-slim AS runtime

# LibreOffice for exact pagination and the PDF download; fonts so a document
# renders in something close to what it asks for rather than a substitute.
# Drop this layer for an image about 400 MB smaller — the app starts and runs
# without it, and says so when a PDF is asked for.
RUN apt-get update && apt-get install --no-install-recommends -y \
        libreoffice-writer \
        fonts-liberation fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY backend/requirements.txt ./
# Patient with the network: pip gives up on a read after fifteen seconds by
# default, and matplotlib and pdfminer are large enough that a slow connection
# hits that and fails the whole build. Ten retries and two minutes of patience
# cost nothing when the network is fine.
RUN pip install --no-cache-dir --timeout 120 --retries 10 -r requirements.txt

COPY backend/app ./app
COPY --from=frontend /build/dist ./static

# Where documents, versions and the signing key live. Mount a volume here or
# every deploy starts an empty workspace.
ENV DOCPILOT_DATA_DIR=/data \
    FRONTEND_DIST=/srv/static \
    PYTHONUNBUFFERED=1 \
    PORT=8000
RUN mkdir -p /data

# Not root: nothing here needs to be, and a container that cannot write outside
# its own data directory is a smaller problem when something goes wrong.
RUN useradd --create-home --uid 10001 formatly && chown -R formatly /srv /data
USER formatly

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", 8000)}/health').read()"

# One worker: the version engine holds a lock per process and SQLite is a file.
# More capacity comes from more containers with their own data, or from moving
# the store to a server, not from more workers over one file.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-keep-alive 75"]
