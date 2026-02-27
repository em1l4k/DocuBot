# Dockerfile для DocuBot
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash docubot
RUN chown -R docubot:docubot /app
USER docubot

# Открываем порт (если нужен для мониторинга)
EXPOSE 8000

# Команда запуска
CMD ["python", "run_bot.py"]
