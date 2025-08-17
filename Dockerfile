FROM python:3.13.1-bookworm

WORKDIR /app/

# Install pipx and then uv using pipx.
# pipx ensures uv is installed in its own isolated environment.
RUN pip install --no-cache-dir pipx && \
    pipx install uv

ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml .
COPY uv.lock .

RUN uv sync --locked

COPY fintra/ /app/fintra/
COPY .env /app/.env
COPY templates/ /app/templates/

EXPOSE 8000 8001

COPY entrypoint.sh .
COPY debug-entrypoint.sh .
