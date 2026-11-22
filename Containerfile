FROM docker.io/library/python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ROLE_DATA_DIR=/data
WORKDIR /app
COPY src/ src/
COPY tests/ tests/
COPY scripts/ scripts/
COPY data/ data/
RUN mkdir /data && chown 10001:10001 /data
USER 10001:10001
CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]
