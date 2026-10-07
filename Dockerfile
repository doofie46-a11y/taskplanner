# TaskPlanner — immagine per la modalità server (Flask + PostgreSQL).
# Uso tipico con docker compose: vedi compose.yaml e la sezione "Docker" del README.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TASKPLANNER_DATA=/data

WORKDIR /app

COPY requirements/base.txt requirements/server.txt requirements/
RUN pip install --no-cache-dir -r requirements/server.txt

COPY . .

# Utente non privilegiato; /data contiene allegati e log (volume)
RUN useradd --system --uid 1000 --no-create-home --home-dir /data taskplanner \
 && mkdir -p /data \
 && chown taskplanner:taskplanner /data
USER taskplanner
VOLUME /data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/login', timeout=4)"

# --preload: lo schema del DB viene creato/migrato una sola volta nel processo
# principale, non in parallelo da ogni worker al primo avvio
CMD ["gunicorn", "--preload", "--workers", "2", "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", "app_server:app"]
