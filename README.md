Приложение для планирования и выполнения произвольных запросов (SQL, API-запросы и другие)

## Стек
Backend: FastAPI
Очереди задач: Dramatiq
Брокер сообщений: Redis
База данных: PostgreSQL
Веб-интерфейс: Jinja2 + HTML
Контейнерезация: Docker

## Установка
Клонируйте репозиторий:

```bash
git clone https://github.com/your-username/queriescheduler.git
```

Перейдите в каталог проекта:

```bash
cd tasks_app
```

Соберите и запустите контейнеры Docker:

```bash
docker-compose up --build
```

Оно будет доступно на локалхосте: **[127.0.0.1:8000](127.0.0.1:8000)**
