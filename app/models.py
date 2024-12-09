# app/models.py
from databases import Database

from pydantic import BaseModel
from typing import Optional

class TaskCreate(BaseModel):
    query: str
    parameters: dict

# Пример модели, где запросы будут выполняться напрямую
class TaskResult:
    def __init__(self, task_id: int, status: str, result: str):
        self.task_id = task_id
        self.status = status
        self.result = result

class TaskCreate(BaseModel):
    query: str  # Запрос, который нужно выполнить
    parameters: Optional[dict] = None  # Параметры для запроса (если они есть)