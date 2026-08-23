FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/app

RUN useradd --create-home --uid 1000 appuser
WORKDIR /home/app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && mkdir -p /home/app/.media_to_text_jobs \
    && chown -R appuser:appuser /home/app

USER appuser

EXPOSE 7860

CMD ["sh", "-c", "uvicorn media_to_text.web:app --host 0.0.0.0 --port ${PORT:-7860}"]
