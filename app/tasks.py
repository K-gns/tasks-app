import os
import dramatiq
from dramatiq import actor
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AsyncIO
from datetime import datetime, timedelta
from app.database_middleware import DatabaseMiddleware
import redis
from .db import database, connect_to_database, disconnect_from_database, fetch_task_by_id
import asyncio

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
@actor(max_retries=3)  # Автоматический перезапуск до 3 раз при сбоях
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

    try:
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


async def schedule_task(task_id: int, scheduled_time: datetime):
    """Добавление задачи в Redis с отложенным временем."""
    timestamp = scheduled_time.timestamp()  # Преобразование в UNIX timestamp
    redis_client.zadd("scheduled_tasks", {task_id: timestamp})
    print(f"Task {task_id} scheduled at {scheduled_time}")


async def process_scheduled_tasks():
    """Периодическая проверка задач в Redis."""
    while True:
        now = datetime.utcnow().timestamp()
        print("process_scheduled_tasks...")

        # Получаем задачи, которые должны быть выполнены
        tasks = redis_client.zrangebyscore("scheduled_tasks", 0, now, start=0, num=10)

        for task_id in tasks:
            task_id = int(task_id)
            print(f"Executing scheduled task {task_id}")

            # Запуск задачи
            execute_task.send(task_id)

            # Удаляем задачу из Redis, так как она была выполнена
            redis_client.zrem("scheduled_tasks", task_id)

        # Пауза между проверками
        await asyncio.sleep(5)  # Проверка каждые 5 секунд


async def add_task_to_schedule(task_id: int, scheduled_time: datetime):
    """Добавление задачи в расписание с отложенным временем."""
    await schedule_task(task_id, scheduled_time)


# Периодическая задача для проверки и выполнения отложенных
async def start_scheduled_task_processor():
    """Запуск задачи, которая будет обрабатывать отложенные задачи."""
    print("Checking for scheduled tasks...")
    while True:
        await process_scheduled_tasks()

# Запуск фонового процесса для обработки отложенных задач
loop = asyncio.get_event_loop()
loop.create_task(start_scheduled_task_processor())  # Запуск фоновой задачи