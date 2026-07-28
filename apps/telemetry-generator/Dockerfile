FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

ENV FASTF1_CACHE_DIR=/app/.fastf1-cache

ENTRYPOINT ["python", "-m", "src.main"]
