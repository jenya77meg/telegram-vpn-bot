FROM python:3.10-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем ca-certificates и curl
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      curl && \
    rm -rf /var/lib/apt/lists/*

COPY bot        ./bot
COPY goods.json ./

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "bot/main.py"]
