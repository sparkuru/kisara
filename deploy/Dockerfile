FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml readme.md ./
COPY src ./src
COPY deploy/kisara-dev-watch.sh /opt/kisara/kisara-dev-watch.sh
COPY deploy/preview-deps.py deploy/preview-probe.py deploy/preview-constraints-py312.txt /opt/kisara/

ARG KISARA_EXTRA=""
RUN python /opt/kisara/preview-deps.py install-system "${KISARA_EXTRA}" \
    && python /opt/kisara/preview-deps.py check "${KISARA_EXTRA}"

RUN chmod 755 /opt/kisara/kisara-dev-watch.sh \
    && useradd --create-home --uid 10001 kisara \
    && mkdir -p /app/state /app/setu \
    && chown -R kisara:kisara /app /opt/kisara
USER kisara

CMD ["python", "-m", "kisara"]
