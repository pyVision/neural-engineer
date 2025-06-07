FROM python:3.11 AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN pip install poetry
RUN poetry config virtualenvs.in-project true
COPY pyproject.toml poetry.lock ./
COPY README.md ./
COPY src/ ./src
COPY templates/ ./templates
COPY .env ./.env
RUN poetry install --no-root

EXPOSE 8000

CMD ["poetry", "run","uvicorn","src.domain_check.main:app","--host", "0.0.0.0", "--reload"]
