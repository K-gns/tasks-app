import json
# import httpx
import os
import dramatiq
import httpx
from databases import Database
from dramatiq import actor, Middleware
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AsyncIO
from datetime import datetime, timedelta
# from app.database_middleware import DatabaseMiddleware
import redis
from .db import database, connect_to_database, disconnect_from_database, fetch_task_by_id
import asyncio

class DatabaseMiddleware(Middleware):
    """Middleware для подключения к базе данных."""
    def before_task(self, broker, message):
        """Подключение к базе перед выполнением задачи."""
        if not database.is_connected:
            broker.logger.debug("Connecting to database.")
            broker.loop.run_until_complete(database.connect())

    def after_task(self, broker, message, result=None, exception=None):
        """Закрытие соединения после выполнения задачи."""
        if database.is_connected:
            broker.logger.debug("Disconnecting from database.")
            broker.loop.run_until_complete(database.disconnect())

# Настройка брокера Redis
redis_host = os.getenv("REDIS_HOST", "redis")
print(f"Connecting to Redis at: {redis_host}")
redis_broker = RedisBroker(host=redis_host)
redis_broker.add_middleware(AsyncIO())
# redis_broker.add_middleware(DatabaseMiddleware())
dramatiq.set_broker(redis_broker)

# Настройка клиента Redis для отложенных задач
redis_client = redis.StrictRedis(host=redis_host, port=6379, db=0)

# Таблицы для хранения задач и результатов
TASKS_TABLE = "tasks"
RESULTS_TABLE = "task_results"

# Actor для обработки задач
@actor(max_retries=3, min_backoff=5, max_backoff=5)  # Автоматический перезапуск до 3 раз при сбоях
async def execute_task(task_id: int):
    if not database.is_connected:
        await database.connect()
    print(f"Processing task {task_id}")
    try:
        task = await fetch_task_by_id(task_id)
        if not task:
            print(f"Task {task_id} not found")
            return

        print(f"Starting task {task_id}")
        await run_task(task_id)
    except Exception as e:
        print(f"Error processing task {task_id}: {e}")


async def run_task(task_id: int):
    task = await fetch_task_by_id(task_id)

    if not task:
        print(f"Task {task_id} not found")
        return

    # Обновляем статус задачи на "running"
    await update_task_status(task_id, "running")

    task_type = task["task_type"]

    try:
        if task_type == "SQL":
            result = await execute_sql_query(task["sql_connstr"], task["query"], task["parameters"] or {})
        elif task_type == "API":
            result = await call_api(task["api_endpoint"], task["parameters"] or {})
        else:
            raise ValueError(f"Unsupported task type: {task_type}")

        # Выполняем задачу (например, выполнение запроса)
        result = f"Executed query: {task['query']} with parameters: {task['parameters']}"

        # Сохраняем результат в таблице результатов
        await save_task_result(task_id, "completed", result)

        # Увеличить счетчик выполнений
        await increment_task_execution_count(task_id)

        print(f"Task {task_id} completed successfully.")

    except Exception as e:
        # В случае ошибки обновляем статус задачи на "failed"
        error_message = str(e)
        await save_task_result(task_id, "failed", error_message)
        print(f"Task {task_id} failed with error: {error_message}")


async def execute_sql_query(connstr: str, query: str, parameters: dict):
    """Выполняет SQL-запрос к базе данных с использованием строки подключения."""
    database = Database(connstr)

    try:
        await database.connect()
        result = await database.execute(query, parameters) #Выполняем запрос
        return result
    except Exception as e:
        raise RuntimeError(f"SQL execution failed: {e}")
    finally:
        await database.disconnect()  # Закрываем подключение


async def call_api(endpoint: str, payload: dict):
    """Выполняет HTTP-запрос к API."""
    """Выполняет HTTP-запрос к API."""
    print("we in call api")
    async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, read=5.0, write=5.0),
            follow_redirects=True
    ) as client:
        try:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"API call failed: {e.response.text}")


async def update_task_status(task_id: int, status: str):
    """Обновление статуса задачи в базе данных."""
    query = f"UPDATE {TASKS_TABLE} SET status = :status WHERE id = :task_id"
    await database.execute(query=query, values={"status": status, "task_id": task_id})


async def save_task_result(task_id: int, status: str, result: str):
    """Сохранение результата выполнения задачи."""
    # Обновляем статус задачи
    await update_task_status(task_id, status)

    # Сохраняем результат в таблицу результатов
    query = f"""
    INSERT INTO {RESULTS_TABLE} (task_id, status, result) 
    VALUES (:task_id, :status, :result)
    """
    values = {"task_id": task_id, "status": status, "result": result}
    await database.execute(query=query, values=values)

async def increment_task_execution_count(task_id: int):
    """Увеличивает счетчик выполнений задачи."""
    query = """
    UPDATE tasks 
    SET executed_count = executed_count + 1, updated_at = :updated_at 
    WHERE id = :task_id
    """
    await database.execute(query, values={"task_id": task_id, "updated_at": datetime.utcnow()})
