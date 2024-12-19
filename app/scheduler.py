import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.db import database, fetch_task_by_id  # Импортируем функцию для работы с БД
from app.tasks import execute_task, update_task_status, \
    TASKS_TABLE  # Функция для выполнения задачи, интеграция с Dramatiq


# Инициализация планировщика
scheduler = AsyncIOScheduler()


# Функция для старта планировщика
def start_scheduler():
    print("Trying to start scheduler...")

    # Запуск планировщика только если он еще не был запущен
    if not scheduler.running:
        scheduler.start()


    # Добавление проверки в планировщик (каждые 5с)
    scheduler.add_job(
        process_scheduled_tasks,
        trigger=IntervalTrigger(seconds=5),
        id="intervalTaskCheck",
    )

    print("Scheduler started...")

async def process_scheduled_tasks():
    """Периодическая проверка задач в БД."""
    current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] Checking for scheduled tasks... ")

    # Получаем задачи, которые должны быть выполнены
    task_ids = await fetch_scheduled_tasks(limit=10)

    for task_id in task_ids:
        print(f"Executing scheduled task {task_id}")

        # Запуск задачи
        execute_task.send(task_id)

        # Обновляем статус задачи на "in_progress"
        await update_task_status(task_id, "in_progress")

async def fetch_scheduled_tasks(limit: int = 10):
    """Получение задач с планируемым временем выполнения."""
    query = f"""
    SELECT id FROM {TASKS_TABLE} 
    WHERE status IN ('scheduled', 'pending')  AND scheduled_time <= :now 
    ORDER BY scheduled_time ASC 
    LIMIT :limit
    """
    now = datetime.utcnow()
    rows = await database.fetch_all(query=query, values={"now": now, "limit": limit})
    return [row["id"] for row in rows]

 #    Создание или обновление задачи в расписании
async def schedule_task(task_id: int, scheduled_time: datetime):
    existing_task = await fetch_task_by_id(task_id)

    if existing_task:
        # Если задача уже существует, обновляем её
        update_query = f"""
            UPDATE {TASKS_TABLE} 
            SET scheduled_time = :scheduled_time, status = 'scheduled'
            WHERE id = :task_id
            """
        await database.execute(
            query=update_query,
            values={"scheduled_time": scheduled_time, "task_id": task_id}
        )
        print(f"Task {task_id} updated with new schedule at {scheduled_time}")

# Функция для остановки планировщика (при необходимости)
def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler stopped...")

start_scheduler()