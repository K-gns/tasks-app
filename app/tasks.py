import os
import dramatiq
from dramatiq import actor
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AsyncIO
from datetime import datetime, timedelta
from app.database_middleware  import DatabaseMiddleware

from .db import database, connect_to_database, disconnect_from_database, fetch_task_by_id

import asyncio

# Настройка брокера Redis
redis_host = os.getenv("REDIS_HOST", "redis")
print(f"Connecting to Redis at: {redis_host}")
redis_broker = RedisBroker(host=redis_host)
redis_broker.add_middleware(AsyncIO())
redis_broker.add_middleware(DatabaseMiddleware())
dramatiq.set_broker(redis_broker)

# Таблицы для хранения задач и результатов
TASKS_TABLE = "tasks"
RESULTS_TABLE = "task_results"

@actor(max_retries=3)   # Автоматический перезапуск до 3 раз при сбоях
async def execute_task(task_id: int):
    if not database.is_connected:
        await database.connect()
    print(f"Processing task {task_id}")
    try:
        query = "SELECT * FROM tasks WHERE id = :task_id"
        task = await database.fetch_one(query, values={"task_id": task_id})
        print(f"Get tasked {task_id}")

        if not task:
            print(f"Task {task_id} not found")
            return

        print(f"Starting Running task {task_id}")
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

        try:
            scheduled_time = task["scheduled_time"]
            if scheduled_time > datetime.utcnow():
                # Задача еще не должна выполняться, откладываем выполнение
                delay = (scheduled_time - datetime.utcnow()).total_seconds()
                print(f"Task {task_id} scheduled to run at {scheduled_time}. Delaying for {delay} seconds.")
                await asyncio.sleep(delay)

            # Выполняем задачу (например, выполнение запроса)
            result = f"Executed query: {task['query']} with parameters: {task['parameters']}"

            # Сохраняем результат в таблице результатов
            await save_task_result(task_id, "completed", result)
            print(f"Task {task_id} completed successfully.")

        except Exception as e:
            # В случае ошибки обновляем статус задачи на "failed"
            error_message = str(e)
            await save_task_result(task_id, "failed", error_message)
            print(f"Task {task_id} failed with error: {error_message}")




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


async def simulate_long_task():
    """Имитация выполнения долгой задачи."""
    await asyncio.sleep(5)
