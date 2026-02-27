# 🚀 Руководство по развертыванию DocuBot

## 📋 Требования

### Системные требования:
- **ОС:** Ubuntu Server 22.04 LTS (рекомендуется)
- **Python:** 3.10+
- **Docker:** 20.10+
- **Docker Compose:** 2.0+

### Программное обеспечение:
- **PostgreSQL:** 14+
- **MinIO:** Latest
- **Nginx:** 1.18+ (опционально)

## 🐳 Развертывание с Docker

### 1. Подготовка

```bash
# Клонируем репозиторий
git clone <repository-url>
cd DOCUBOT1

# Копируем файл конфигурации
cp env.example .env

# Редактируем конфигурацию
nano .env
```

### 2. Настройка .env

```env
# Обязательные параметры
BOT_TOKEN=your_bot_token_here
DATABASE_URL=postgresql+psycopg2://docubot:docubot_password@postgres:5432/docubot
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=docubot
MINIO_SECURE=false

# Дополнительные параметры
WHITELIST_PATH=access/whitelist.csv
MAX_FILE_MB=20
PRESIGN_TTL_MIN=60
LOG_LEVEL=INFO
```

### 3. Создание whitelist

```bash
# Создаем директорию для whitelist
mkdir -p access

# Создаем файл whitelist.csv
cat > access/whitelist.csv << EOF
telegram_id,role,full_name,is_active
579583676,admin,Администратор,true
123456789,manager,Менеджер,true
987654321,employee,Сотрудник,true
EOF
```

### 4. Запуск с Docker Compose

```bash
# Запускаем все сервисы
docker-compose up -d

# Проверяем статус
docker-compose ps

# Просматриваем логи
docker-compose logs -f docubot
```

### 5. Проверка работоспособности

```bash
# Проверяем подключение к базе данных
docker-compose exec docubot python -c "from bot.db.session import engine; print('DB OK')"

# Проверяем MinIO
docker-compose exec docubot python -c "from bot.services.storage import _client; print('MinIO OK')"

# Проверяем бота
docker-compose exec docubot python -c "from bot.main import bot; print('Bot OK')"
```

## 🔧 Ручное развертывание

### 1. Установка зависимостей

```bash
# Устанавливаем Python 3.10+
sudo apt update
sudo apt install python3.10 python3.10-pip python3.10-venv

# Создаем виртуальное окружение
python3.10 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install -r requirements.txt
```

### 2. Настройка PostgreSQL

```bash
# Устанавливаем PostgreSQL
sudo apt install postgresql postgresql-contrib

# Создаем базу данных
sudo -u postgres psql
CREATE DATABASE docubot;
CREATE USER docubot WITH PASSWORD 'docubot_password';
GRANT ALL PRIVILEGES ON DATABASE docubot TO docubot;
\q
```

### 3. Настройка MinIO

```bash
# Устанавливаем MinIO
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
sudo mv minio /usr/local/bin/

# Создаем директорию для данных
sudo mkdir -p /opt/minio/data
sudo chown -R minio:minio /opt/minio

# Запускаем MinIO
minio server /opt/minio/data --console-address ":9001"
```

### 4. Запуск бота

```bash
# Активируем виртуальное окружение
source venv/bin/activate

# Запускаем бота
python run_bot.py
```

## 📊 Мониторинг и логирование

### 1. Логи

```bash
# Просмотр логов Docker
docker-compose logs -f docubot

# Логи приложения
tail -f logs/bot.log

# Логи базы данных
docker-compose logs -f postgres

# Логи MinIO
docker-compose logs -f minio
```

### 2. Мониторинг

```bash
# Статус контейнеров
docker-compose ps

# Использование ресурсов
docker stats

# Проверка здоровья
curl http://localhost/health
```

## 🔒 Безопасность

### 1. Настройка файрвола

```bash
# Разрешаем только необходимые порты
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

### 2. SSL сертификаты

```bash
# Устанавливаем Certbot
sudo apt install certbot python3-certbot-nginx

# Получаем сертификат
sudo certbot --nginx -d your-domain.com
```

### 3. Резервное копирование

```bash
# Создаем бэкап базы данных
docker-compose exec postgres pg_dump -U docubot docubot > backup.sql

# Создаем бэкап MinIO
docker-compose exec minio mc mirror /data /backup
```

## 🚀 Обновление

### 1. Обновление кода

```bash
# Останавливаем сервисы
docker-compose down

# Обновляем код
git pull

# Пересобираем образы
docker-compose build

# Запускаем сервисы
docker-compose up -d
```

### 2. Миграции базы данных

```bash
# Применяем миграции
docker-compose exec docubot python -c "from bot.db.init_schema import init_schema; init_schema()"
```

## 🛠️ Устранение неполадок

### 1. Проблемы с подключением к БД

```bash
# Проверяем статус PostgreSQL
docker-compose exec postgres pg_isready

# Проверяем подключение
docker-compose exec docubot python -c "from bot.db.session import engine; print(engine.execute('SELECT 1').scalar())"
```

### 2. Проблемы с MinIO

```bash
# Проверяем статус MinIO
docker-compose exec minio mc admin info

# Проверяем бакет
docker-compose exec minio mc ls docubot
```

### 3. Проблемы с ботом

```bash
# Проверяем токен
docker-compose exec docubot python -c "from bot.config import BOT_TOKEN; print('Token OK' if BOT_TOKEN else 'Token MISSING')"

# Проверяем whitelist
docker-compose exec docubot python -c "from bot.rbac import WhitelistStore; store = WhitelistStore('access/whitelist.csv'); print(f'Users: {len(store.users)}')"
```

## 📈 Масштабирование

### 1. Горизонтальное масштабирование

```yaml
# docker-compose.yml
services:
  docubot:
    deploy:
      replicas: 3
    environment:
      - NODE_ID=${HOSTNAME}
```

### 2. Load Balancer

```nginx
# nginx.conf
upstream docubot {
    server docubot_1:8000;
    server docubot_2:8000;
    server docubot_3:8000;
}
```

### 3. Кэширование

```bash
# Устанавливаем Redis
docker-compose exec docubot pip install redis

# Настраиваем кэширование
export REDIS_URL=redis://redis:6379
```

## 📞 Поддержка

При возникновении проблем:

1. **Проверьте логи:** `docker-compose logs -f docubot`
2. **Проверьте конфигурацию:** `.env` файл
3. **Проверьте подключения:** БД, MinIO, Telegram API
4. **Обратитесь к документации:** README.md
5. **Создайте issue:** в репозитории проекта
