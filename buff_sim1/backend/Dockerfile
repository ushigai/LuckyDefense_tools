FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py ./app.py
EXPOSE 8000
CMD ["gunicorn", "app:app", "-w", "2", "-k", "gthread", "--threads", "2", "--timeout", "120", "--graceful-timeout", "30", "--keep-alive", "5", "--max-requests", "2000", "--max-requests-jitter", "200", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "--bind", "0.0.0.0:8000"]
