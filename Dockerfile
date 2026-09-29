# This file belongs at the repo root, next to rogerwilco/ (the skill) and app/ (this folder):
#   docker build -t rogerwilco --build-arg GIT_COMMIT=$(git rev-parse --short HEAD) .
#   docker run --rm -p 8080:8080 rogerwilco
FROM python:3.12-slim

ENV RW_SKILL_DIR=/srv/rogerwilco \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

# Dependencies first, so a code change does not reinstall them.
COPY app/requirements.txt /srv/app/requirements.txt
RUN pip install -r /srv/app/requirements.txt

COPY rogerwilco/ /srv/rogerwilco/
COPY app/ /srv/app/

# Late, so a new commit only rebuilds from here.
ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=${GIT_COMMIT}

# A numeric user, so orchestrators that require a non-root user can verify it.
RUN useradd --system --uid 10001 --no-create-home rw
USER 10001

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
