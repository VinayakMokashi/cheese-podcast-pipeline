# Use the official Debian-hosted Python image
FROM python:3.12-slim-bookworm

ENV LANG=C.UTF-8
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/home/app/.venv

# Install uv and create a non-root user. No apt packages needed:
# every dependency ships as a prebuilt wheel.
RUN pip install --no-cache-dir uv && \
    useradd -ms /bin/bash app -d /home/app -u 1000 && \
    mkdir -p /app && \
    chown app:app /app

USER app
WORKDIR /app

# Dependencies first, so editing the code doesn't reinstall them
COPY --chown=app:app pyproject.toml uv.lock ./
RUN uv sync --locked

# Then the code, which changes often
COPY --chown=app:app . ./

EXPOSE 9100
CMD ["/home/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9100"]
