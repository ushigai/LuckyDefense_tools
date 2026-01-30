FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY dps_sim1/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY dps_sim1 ./dps_sim1
COPY data ./data

EXPOSE 8000

CMD ["gunicorn", "dps_sim1.app:app", \
     "-w", "2", \
     "-k", "gthread", "--threads", "2", \
     "--timeout", "120", "--graceful-timeout", "30", \
     "--keep-alive", "5", \
     "--max-requests", "1000", "--max-requests-jitter", "100", \
     "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", \
     "--bind", "0.0.0.0:8000"]
