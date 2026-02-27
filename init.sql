-- Инициализация базы данных DocuBot
-- Этот файл выполняется при первом запуске PostgreSQL

-- Создаем базу данных (если не существует)
-- CREATE DATABASE docubot;

-- Создаем пользователя (если не существует)
-- CREATE USER docubot WITH PASSWORD 'docubot_password';

-- Предоставляем права
-- GRANT ALL PRIVILEGES ON DATABASE docubot TO docubot;

-- Подключаемся к базе данных
\c docubot;

-- Создаем расширения
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Создаем схему (если нужно)
-- CREATE SCHEMA IF NOT EXISTS docubot;

-- Устанавливаем часовой пояс
SET timezone = 'UTC';
