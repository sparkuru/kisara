FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml readme.md ./
COPY src ./src
COPY deploy/kisara-dev-watch.sh /opt/kisara/kisara-dev-watch.sh

RUN python -m pip install --no-cache-dir .

RUN chmod 755 /opt/kisara/kisara-dev-watch.sh \
    && useradd --create-home --uid 10001 kisara \
    && mkdir -p /app/state /app/setu \
    && chown -R kisara:kisara /app /opt/kisara
USER kisara

CMD ["python", "-m", "kisara"]
