FROM python:3.11-slim

WORKDIR /app

ENV PORT=8000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --uid 10001 appuser

COPY app.py .
COPY templates/ templates/

RUN chown -R appuser:appuser /app

EXPOSE 8000
USER 10001
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
