# MindTrack — production image for Google Cloud Run.
# Runs the existing Flask app (run.py -> create_app()) under Gunicorn.
# Flask's debug server is never used here: run.py only calls app.run(debug=True)
# under `if __name__ == "__main__"`, which Gunicorn does not execute.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MINDTRACK_ENV=production

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Secrets, local databases and the venv are excluded by .dockerignore.
COPY . .

RUN useradd --create-home --uid 10001 mindtrack && chown -R mindtrack /app
USER mindtrack

# Cloud Run provides $PORT (8080 by default). One worker with threads suits a
# 1-vCPU instance; --timeout 0 lets Cloud Run's request timeout apply instead.
CMD exec gunicorn --bind ":${PORT:-8080}" --workers 1 --threads 8 --timeout 0 run:app
