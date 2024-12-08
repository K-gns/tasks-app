from fastapi import FastAPI
from .tasks import execute_task
from .models import TaskCreate


app = FastAPI()



@app.post("/tasks/")
async def create_task(task: TaskCreate):
    task_id = 1  # Уникальный идентификатор задачи
    execute_task.send(task.query, task.parameters, task_id)  # Отправляем задачу в очередь
    return {"message": "Task enqueued", "task_id": task_id}
