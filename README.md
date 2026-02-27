# DOCUBOT - Система управления документами

Telegram-бот для управления корпоративными документами с системой контроля доступа.

## 🏗️ Структура проекта

```
DOCUBOT1/
├── bot/                          # Основной код бота
│   ├── main.py                  # Главный файл бота (ЕДИНСТВЕННЫЙ main)
│   ├── config.py                 # Конфигурация
│   ├── rbac.py                   # Система ролей
│   ├── db/                       # База данных
│   │   ├── session.py           # Подключение к БД
│   │   ├── init_schema.py       # Инициализация схемы
│   │   └── schema.sql           # SQL схема
│   ├── handlers/                # Обработчики
│   │   ├── keyboards/           # Клавиатуры
│   │   │   └── keyboards.py     # Основные клавиатуры
│   │   └── commands/            # Команды и обработчики
│   │       ├── start.py         # Команда /start
│   │       ├── profile.py       # Команда /profile
│   │       ├── documents.py     # Команда /my_docs
│   │       ├── admin.py         # Админские команды
│   │       └── buttons.py       # Обработчики кнопок
│   ├── middlewares/             # Middleware
│   │   └── rbac.py             # RBAC middleware
│   └── services/                # Сервисы
│       ├── repo.py             # Работа с БД
│       └── storage.py           # Хранение файлов
├── access/                      # Контроль доступа
│   └── whitelist.csv           # Список пользователей
├── requirements.txt            # Зависимости
└── run_bot.py                  # Скрипт запуска
```

## 🚀 Запуск

```bash
# Основной способ
python run_bot.py

# Или напрямую
python -m bot.main
```

## 📋 Функции

- 📄 **Загрузка документов** (PDF, DOCX)
- 🔄 **Версионирование** документов
- 👥 **Контроль доступа** (employee, manager, admin)
- 💾 **Хранение** в MinIO
- 🗄️ **База данных** PostgreSQL

## ⚙️ Настройка

1. Создайте `.env` файл с переменными:
```env
BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql://user:pass@localhost:5432/db
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Запустите бота:
```bash
python run_bot.py
```

