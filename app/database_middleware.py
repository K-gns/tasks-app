import asyncio
from dramatiq import Middleware
from .db import connect_to_database, disconnect_from_database

class DatabaseMiddleware(Middleware):
    """Middleware для управления подключением к базе данных."""

    def before_worker_boot(self, broker, worker):
        """Подключение к базе данных при старте worker."""
        asyncio.run(connect_to_database())

    def after_worker_shutdown(self, broker, worker):
        """Отключение от базы данных при завершении worker."""
        asyncio.run(disconnect_from_database())

# Инициализация middleware
database_middleware = DatabaseMiddleware()
