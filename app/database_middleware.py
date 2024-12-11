import dramatiq
from dramatiq.middleware import Middleware
from app.db import database

class DatabaseMiddleware(Middleware):
    async def before_enqueue(self, broker, message):
        print("Connecting to database before processing message")
        if not database.is_connected:
            await database.connect()

    async def after_enqueue(self, broker, message, *, result=None, exception=None):
        print("Disconnecting from database after processing message")
        if database.is_connected:
            await database.disconnect()
