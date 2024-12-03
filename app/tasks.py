from dramatiq import actor
from .db import database
import asyncio

@actor
def execute_task(query: str, parameters: dict, task_id: int):
    asyncio.run(run_task(query, parameters, task_id))

async def run_task(query: str, parameters: dict, task_id: int):
    await simulate_long_task()

    query = "INSERT INTO task_results (task_id, status, result) VALUES (:task_id, :status, :result)"
    values = {"task_id": task_id, "status": "completed", "result": "Task finished"}
    await database.execute(query=query, values=values)

async def simulate_long_task():
    await asyncio.sleep(5)
