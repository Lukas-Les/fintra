FROM python:3.13.1-bookworm

WORKDIR /app

COPY requirements/main.txt requirements/main.txt

RUN python -m venv .venv && \
    . .venv/bin/activate && \
    pip install --no-cache-dir -r requirements/main.txt

COPY fintra/ /app/fintra/

EXPOSE 8000 8001

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python -m fintra"]
