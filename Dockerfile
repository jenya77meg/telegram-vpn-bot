FROM python:3.12-slim-bullseye

# Dockerfile (vpn_bot)
FROM python:3.12-slim-bullseye

WORKDIR /usr/src/app

# 1) Устанавливаем системные зависимости и сертификаты через apt
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# 2) Копируем и устанавливаем Python-зависимости
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 3) Копируем весь код бота
COPY . .

# 4) Запускаем бота
CMD ["python3", "-m", "bot"]
