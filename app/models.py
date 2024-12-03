# app/models.py
from databases import Database

# Пример модели, где запросы будут выполняться напрямую
class TaskResult:
    def __init__(self, task_id: int, status: str, result: str):
        self.task_id = task_id
        self.status = status
        self.result = result
