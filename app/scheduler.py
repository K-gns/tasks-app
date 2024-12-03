from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from app.db import get_db  # Импортируем функцию для работы с БД
from app.models import Task  # Модель для задач
from app.tasks import execute_task  # Функция для выполнения задачи, интеграция с Dramatiq


# Функция для выполнения задачи
def schedule_task(query: str, parameters: dict, task_id: str):
    print(f"Executing task {task_id} with query: {query} and parameters: {parameters}")

    # Пример запроса к БД (можно изменить на свою логику)
    with get_db() as db:
        result = db.execute(query, parameters)
        # Задача может быть выполнена через Dramatiq
        execute_task.delay(result)


# Инициализация планировщика
scheduler = BackgroundScheduler()


# Функция для старта планировщика
def start_scheduler():
    # Запуск планировщика только если он еще не был запущен
    if not scheduler.running:
        scheduler.start()

    # Добавление задачи в планировщик (например, каждые 1 час)
    query = "SELECT * FROM users WHERE id = %s"
    parameters = {"id": 1}
    task_id = "task_1"
    scheduler.add_job(schedule_task, 'interval', hours=1, args=[query, parameters, task_id])

    print("Scheduler started...")


# Функция для остановки планировщика (если нужно)
def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler stopped...")
