# app/main.py
from fastapi import FastAPI, HTTPException
from .tasks import execute_task
from .schemas import TaskCreate, TaskResultOut
from .db import database, create_tables
from .models import TaskResult
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI()
scheduler = BackgroundScheduler()

@app.on_event("startup")
async def start_scheduler():
    # Подключение к базе данных
    await database.connect()
    # Создание таблицы, если она не существует
    await create_tables()
    # Запуск задачи каждую минуту
    scheduler.add_job(job_function, 'interval', minutes=1)
    scheduler.start()

@app.on_event("shutdown")
async def shutdown():
    # Отключение от базы данных при завершении работы приложения
    await database.disconnect()

def job_function():
    print("Scheduled task is running...")

@app.post("/tasks/")
async def create_task(task: TaskCreate):
    task_id = 1  # Здесь должно быть уникальное значение
    await execute_task(task.query, task.parameters, task_id)  # Асинхронный вызов
    return {"message": "Task created", "task_id": task_id}

@app.get("/tasks/{task_id}", response_model=TaskResultOut)
async def get_task_result(task_id: int):
    query = f"SELECT * FROM task_results WHERE task_id = {task_id}"
    result = await database.fetch_one(query)
    if result:
        return result  # Возвращаем результат из базы данных
    raise HTTPException(status_code=404, detail="Task not found")
