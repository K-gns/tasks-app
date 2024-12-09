import os
import dramatiq
from dramatiq import actor
from dramatiq.brokers.redis import RedisBroker

from .db import database  # Предполагается, что database — это подключение к базе через `databases`
import asyncio

# Настройка брокера Redis
redis_host = os.getenv("REDIS_HOST", "redis")
print(f"Connecting to Redis at: {redis_host}")
redis_broker = RedisBroker(host=redis_host)
dramatiq.set_broker(redis_broker)

# Таблицы для хранения задач и результатов
TASKS_TABLE = "tasks"
RESULTS_TABLE = "task_results"


@actor(max_retries=3)  # Автоматический перезапуск до 3 раз при сбоях
def execute_task(task_id: int):
    """Основной актор для выполнения задачи."""
    asyncio.run(run_task(task_id))


async def run_task(task_id: int):
    """Выполнение задачи с обновлением статуса в базе данных."""
    # Получаем информацию о задаче
    query = f"SELECT query, parameters FROM {TASKS_TABLE} WHERE id = :task_id"
    task = await database.fetch_one(query=query, values={"task_id": task_id})

    if not task:
        print(f"Task {task_id} not found")
        return

    # Обновляем статус задачи на "running"
    await update_task_status(task_id, "running")

    try:
        # Имитация выполнения задачи
        await simulate_long_task()

        # Здесь добавьте реальную логику выполнения задачи, например выполнение SQL-запроса
        # или вызов внешнего API. В данном примере используется заглушка.
        result = f"Executed query: {task['query']} with parameters: {task['parameters']}"

        # Сохраняем результат в базу данных
        await save_task_result(task_id, "completed", result)
        print(f"Task {task_id} completed successfully")
    except Exception as e:
        # Обновляем статус задачи на "failed" в случае ошибки
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
