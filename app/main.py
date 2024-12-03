from fastapi import FastAPI
import dramatiq
from dramatiq.brokers.redis import RedisBroker
from .tasks import execute_task
from .models import TaskCreate


app = FastAPI()

# Настройка брокера Redis
redis_host = "redis"  # Это имя контейнера из docker-compose.yml
redis_broker = RedisBroker(host=redis_host, port=6379)
dramatiq.set_broker(redis_broker)

@app.post("/tasks/")
async def create_task(task: TaskCreate):
    task_id = 1  # Уникальный идентификатор задачи
    execute_task.send(task.query, task.parameters, task_id)  # Отправляем задачу в очередь
    return {"message": "Task enqueued", "task_id": task_id}
