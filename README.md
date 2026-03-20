# Дейтинг-бот для Telegram

## Краткое описание
Телеграм-бот для знакомств, позволяющий пользователям находить новых людей для общения и построения отношений на основе общих интересов и предпочтений.

## Функциональность
- Регистрация и создание анкеты с фотографиями, описанием, интересами и параметрами поиска.
- Просмотр анкет других пользователей с возможностью лайка или пропуска.
- Взаимные лайки открывают чат для общения.
- Фильтрация анкет по полу, возрасту, городу и интересам.
- Личный кабинет с возможностью редактирования анкеты и настроек поиска.
- Административная панель для модерации контента и управления пользователями.
- Уведомления о новых лайках, совпадениях и сообщениях.

## Технологии
- Язык: Python
- Фреймворк: python-telegram-bot
- База данных: PostgreSQL
- ORM: SQLAlchemy
- Кэширование: Redis
- Контейнеризация: Docker, Docker Compose
- Логирование: structlog
- Тестирование: pytest

## Описание сервисов

### Telegram Bot Service (bot.py)
Основной сервис, который принимает и обрабатывает команды и сообщения от пользователей Telegram. Использует python-telegram-bot для взаимодействия с Telegram API. Управляет состояниями диалогов, клавиатурами и маршрутизацией запросов к соответствующим обработчикам.

### User Service (services/user_service.py)
Сервис управления пользователями. Отвечает за регистрацию новых пользователей, получение и обновление профилей, проверку статуса регистрации. Взаимодействует с базой данных через модели SQLAlchemy.

### Profile Service (services/profile_service.py)
Сервис управления анкетами. Обеспечивает создание, редактирование и удаление анкет. Управляет загрузкой и хранением фотографий, обработкой интересов и параметров поиска. Формирует список анкет для показа с учетом фильтров и приоритетов.

### Matching Service (services/matching_service.py)
Сервис обработки взаимных симпатий. Регистрирует лайки и дизлайки, проверяет наличие взаимных лайков. При возникновении взаимности создает чат и отправляет уведомления обоим пользователям. Отвечает за генерацию очереди анкет для показа.

### Chat Service (services/chat_service.py)
Сервис управления чатами. Создает новые чаты после взаимных лайков, сохраняет историю сообщений, проверяет права доступа к чату. Предоставляет методы для отправки сообщений и получения списка активных чатов пользователя.

### Notification Service (services/notification_service.py)
Сервис уведомлений. Отвечает за отправку пользователям уведомлений о новых лайках, совпадениях и сообщениях. Использует Redis для очередей уведомлений и кэширования состояний.

### Admin Service (services/admin_service.py)
Сервис административной панели. Предоставляет методы для модерации анкет, блокировки пользователей, получения статистики и управления системными настройками. Доступен только для пользователей с правами администратора.

### Media Service (services/media_service.py)
Сервис обработки медиафайлов. Управляет загрузкой, хранением и оптимизацией фотографий анкет. Обрабатывает изображения для уменьшения размера и создания превью.

### Filter Service (services/filter_service.py)
Сервис фильтрации анкет. Формирует SQL-запросы на основе параметров поиска пользователя. Учитывает возрастные диапазоны, географические ограничения, интересы и другие критерии отбора.

### Cache Service (services/cache_service.py)
Сервис кэширования. Обеспечивает временное хранение часто запрашиваемых данных в Redis. Кэширует профили пользователей, списки анкет и сессионные данные для снижения нагрузки на базу данных.

## Схема данных в БД

### Таблица users
Хранит основную информацию о пользователях Telegram.
- id (SERIAL, PRIMARY KEY) - уникальный идентификатор пользователя
- telegram_id (BIGINT, UNIQUE, NOT NULL) - идентификатор пользователя в Telegram
- username (VARCHAR(64)) - username из Telegram
- first_name (VARCHAR(128)) - имя пользователя
- last_name (VARCHAR(128)) - фамилия пользователя
- is_active (BOOLEAN, DEFAULT TRUE) - активен ли аккаунт
- is_admin (BOOLEAN, DEFAULT FALSE) - наличие прав администратора
- is_banned (BOOLEAN, DEFAULT FALSE) - заблокирован ли пользователь
- created_at (TIMESTAMP, DEFAULT NOW()) - дата регистрации в боте
- updated_at (TIMESTAMP, DEFAULT NOW()) - дата последнего обновления

### Таблица profiles
Содержит анкетные данные пользователей.
- id (SERIAL, PRIMARY KEY) - уникальный идентификатор анкеты
- user_id (INTEGER, FOREIGN KEY REFERENCES users(id) ON DELETE CASCADE) - связь с пользователем
- gender (VARCHAR(16)) - пол (male, female, other)
- birth_date (DATE) - дата рождения
- city (VARCHAR(128)) - город проживания
- latitude (DECIMAL(10, 8)) - широта для геопоиска
- longitude (DECIMAL(11, 8)) - долгота для геопоиска
- bio (TEXT) - текстовое описание анкеты
- search_gender (VARCHAR(16)) - предпочтительный пол для поиска
- search_age_min (INTEGER) - минимальный возраст поиска
- search_age_max (INTEGER) - максимальный возраст поиска
- search_distance_km (INTEGER, DEFAULT 50) - радиус поиска в километрах
- is_completed (BOOLEAN, DEFAULT FALSE) - завершено ли заполнение анкеты
- created_at (TIMESTAMP, DEFAULT NOW()) - дата создания анкеты
- updated_at (TIMESTAMP, DEFAULT NOW()) - дата последнего обновления

### Таблица photos
Хранит фотографии анкет.
- id (SERIAL, PRIMARY KEY) - уникальный идентификатор фото
- profile_id (INTEGER, FOREIGN KEY REFERENCES profiles(id) ON DELETE CASCADE) - связь с анкетой
- file_id (VARCHAR(256), NOT NULL) - идентификатор файла в Telegram
- file_path (VARCHAR(512)) - путь к файлу в хранилище
- order_index (INTEGER, DEFAULT 0) - порядковый номер фотографии
- is_main (BOOLEAN, DEFAULT FALSE) - является ли главной фотографией
- created_at (TIMESTAMP, DEFAULT NOW()) - дата загрузки

### Таблица interests
Справочная таблица возможных интересов.
- id (SERIAL, PRIMARY KEY) - уникальный идентификатор интереса
- name (VARCHAR(64), UNIQUE, NOT NULL) - название интереса
- category (VARCHAR(64)) - категория интереса
- created_at (TIMESTAMP, DEFAULT NOW()) - дата создания

### Таблица profile_interests
Связующая таблица между анкетами и интересами.
- profile_id (INTEGER, FOREIGN KEY REFERENCES profiles(id) ON DELETE CASCADE) - идентификатор анкеты
- interest_id (INTEGER, FOREIGN KEY REFERENCES interests(id) ON DELETE CASCADE) - идентификатор интереса
- created_at (TIMESTAMP, DEFAULT NOW()) - дата добавления
- PRIMARY KEY (profile_id, interest_id)

### Таблица likes
Фиксирует лайки и дизлайки пользователей.
- id (SERIAL, PRIMARY KEY) - уникальный идентификатор
- from_profile_id (INTEGER, FOREIGN KEY REFERENCES profiles(id) ON DELETE CASCADE) - анкета, которая ставит лайк
- to_profile_id (INTEGER, FOREIGN KEY REFERENCES profiles(id) ON DELETE CASCADE) - анкета, на которую ставят лайк
- like_type (VARCHAR(16), NOT NULL) - тип действия (like, dislike)
- is_mutual (BOOLEAN, DEFAULT FALSE) - флаг взаимного лайка
- created_at (TIMESTAMP, DEFAULT NOW()) - дата действия
- UNIQUE (from_profile_id, to_profile_id)

### Таблица chats
Содержит информацию о чатах между пользователями.
- id (SERIAL, PRIMARY KEY) - уникальный идентификатор чата
- profile1_id (INTEGER, FOREIGN KEY REFERENCES profiles(id) ON DELETE CASCADE) - первый участник чата
- profile2_id (INTEGER, FOREIGN KEY REFERENCES profiles(id) ON DELETE CASCADE) - второй участник чата
- is_active (BOOLEAN, DEFAULT TRUE) - активен ли чат
- created_at (TIMESTAMP, DEFAULT NOW()) - дата создания чата
- last_message_at (TIMESTAMP, DEFAULT NOW()) - дата последнего сообщения

### Таблица messages
Хранит историю сообщений в чатах.
- id (SERIAL, PRIMARY KEY) - уникальный идентификатор сообщения
- chat_id (INTEGER, FOREIGN KEY REFERENCES chats(id) ON DELETE CASCADE) - идентификатор чата
- sender_profile_id (INTEGER, FOREIGN KEY REFERENCES profiles(id) ON DELETE CASCADE) - отправитель сообщения
- message_text (TEXT) - текст сообщения
- is_read (BOOLEAN, DEFAULT FALSE) - прочитано ли сообщение
- created_at (TIMESTAMP, DEFAULT NOW()) - дата отправки

### Таблица reports
Хранит жалобы пользователей.
- id (SERIAL, PRIMARY KEY) - уникальный идентификатор жалобы
- reporter_profile_id (INTEGER, FOREIGN KEY REFERENCES profiles(id) ON DELETE CASCADE) - анкета, подавшая жалобу
- reported_profile_id (INTEGER, FOREIGN KEY REFERENCES profiles(id) ON DELETE CASCADE) - анкета, на которую пожаловались
- reason (VARCHAR(256), NOT NULL) - причина жалобы
- status (VARCHAR(32), DEFAULT 'pending') - статус обработки (pending, reviewed, dismissed)
- moderator_comment (TEXT) - комментарий модератора
- created_at (TIMESTAMP, DEFAULT NOW()) - дата создания жалобы
- resolved_at (TIMESTAMP) - дата разрешения

### Таблица notifications
Хранит уведомления для пользователей.
- id (SERIAL, PRIMARY KEY) - уникальный идентификатор уведомления
- user_id (INTEGER, FOREIGN KEY REFERENCES users(id) ON DELETE CASCADE) - получатель уведомления
- notification_type (VARCHAR(32), NOT NULL) - тип уведомления (like, match, message)
- payload (JSONB) - дополнительные данные уведомления
- is_sent (BOOLEAN, DEFAULT FALSE) - отправлено ли уведомление
- is_read (BOOLEAN, DEFAULT FALSE) - прочитано ли уведомление
- created_at (TIMESTAMP, DEFAULT NOW()) - дата создания

### Таблица views_history
Фиксирует просмотры анкет для формирования очереди показа.
- id (SERIAL, PRIMARY KEY) - уникальный идентификатор
- viewer_profile_id (INTEGER, FOREIGN KEY REFERENCES profiles(id) ON DELETE CASCADE) - анкета просматривающего
- viewed_profile_id (INTEGER, FOREIGN KEY REFERENCES profiles(id) ON DELETE CASCADE) - просмотренная анкета
- viewed_at (TIMESTAMP, DEFAULT NOW()) - дата просмотра
- UNIQUE (viewer_profile_id, viewed_profile_id)

## Индексы для оптимизации
- users_telegram_id_idx ON users (telegram_id)
- profiles_user_id_idx ON profiles (user_id)
- profiles_gender_idx ON profiles (gender)
- profiles_city_idx ON profiles (city)
- profiles_search_gender_idx ON profiles (search_gender)
- likes_from_profile_idx ON likes (from_profile_id)
- likes_to_profile_idx ON likes (to_profile_id)
- likes_mutual_idx ON likes (is_mutual)
- chats_profiles_idx ON chats (profile1_id, profile2_id)
- messages_chat_id_idx ON messages (chat_id)
- messages_created_at_idx ON messages (created_at)
- notifications_user_id_idx ON notifications (user_id)
- reports_status_idx ON reports (status)
- views_history_viewer_idx ON views_history (viewer_profile_id)

## Установка и запуск

### Требования
- Python 3.9 или выше
- PostgreSQL 13 или выше
- Redis 6 или выше
- Docker и Docker Compose (опционально)

### Локальный запуск
1. Клонировать репозиторий:
   git clone https://github.com/shaurmyau/project_3.git
   cd project_3

2. Создать виртуальное окружение и установить зависимости:
   python -m venv venv
   source venv/bin/activate # для Linux/Mac
   venv\Scripts\activate # для Windows
   pip install -r requirements.txt

3. Создать файл .env на основе .env.example и заполнить его:
   BOT_TOKEN=ваш_токен_бота
   DATABASE_URL=postgresql://user:password@localhost/dbname
   REDIS_URL=redis://localhost:6379

4. Применить миграции базы данных:
   alembic upgrade head

5. Запустить бота:
   python bot.py

### Запуск с помощью Docker
1. Убедиться, что установлены Docker и Docker Compose.
2. Заполнить файл .env необходимыми значениями.
3. Выполнить команду:
   docker-compose up -d

## Структура проекта

      bot/ - основная директория с кодом бота
        handlers/ - обработчики команд и сообщений
        keyboards/ - клавиатуры и инлайн-кнопки
        states/ - состояния для ConversationHandler
        utils/ - вспомогательные функции и утилиты
        models/ - модели базы данных
        services/ - бизнес-логика и внешние сервисы
      migrations/ - миграции базы данных
      tests/ - тесты
      config.py - конфигурация приложения
      bot.py - точка входа

## Переменные окружения
   
      Переменная         Описание
      BOT_TOKEN          Токен телеграм-бота
      DATABASE_URL       URL подключения к PostgreSQL
      REDIS_URL          URL подключения к Redis
      ADMIN_IDS          Список ID администраторов через запятую
      DEBUG              Режим отладки

## Тестирование
Для запуска тестов выполнить:
pytest tests/

## Деплой
Пример настройки развертывания на сервере с использованием Docker и Nginx:
1. Скопировать проект на сервер.
2. Установить Docker и Docker Compose.
3. Заполнить .env файл на сервере.
4. Запустить docker-compose up -d.
5. Настроить Nginx для проксирования запросов (если требуется).

## Лицензия
Проект распространяется под лицензией MIT. Подробнее см. файл LICENSE.
