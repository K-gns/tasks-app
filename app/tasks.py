# app/tasks.py
from .models import TaskResult
from .db import database
import time  # Для имитации выполнения задачи


async def execute_task(query: str, parameters: dict, task_id: int):
    # Имитация выполнения задачи
    await simulate_long_task()  # Задача выполняется асинхронно
    task_result = TaskResult(task_id=task_id, status="completed", result="Task finished")  # Пример результата задачи

    # Сохранение результата в базу данных
    # Для этого нужно создать сессию базы данных через database
    query = f"INSERT INTO task_results (task_id, status, result) VALUES ({task_id}, 'completed', 'Task finished')"
    await database.execute(query)  # Пример асинхронной записи в базу данных


async def simulate_long_task():
    time.sleep(5)  # Симуляция долгой работы (можно заменить на реальный код)
