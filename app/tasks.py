import os
import dramatiq
from dramatiq import actor
from dramatiq.brokers.redis import RedisBroker

from .db import database
import asyncio

# Настройка брокера Redis
redis_host = os.getenv("REDIS_HOST")
print("Connecting to Redis at:", os.getenv("REDIS_HOST", "redis"))
redis_broker = RedisBroker(host=redis_host)
dramatiq.set_broker(redis_broker)


@actor
def execute_task(query: str, parameters: dict, task_id: int):
    asyncio.run(run_task(query, parameters, task_id))

async def run_task(query: str, parameters: dict, task_id: int):
    await simulate_long_task()

    query = "INSERT INTO task_results (task_id, status, result) VALUES (:task_id, :status, :result)"
    values = {"task_id": task_id, "status": "completed", "result": "Task finished"}
    # await database.execute(query=query, values=values)
    print("worker_task_done")

async def simulate_long_task():
    await asyncio.sleep(5)
