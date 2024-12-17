from datetime import datetime
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import RedirectResponse

from .scheduler import start_scheduler, schedule_task
from .models import TaskCreate
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from .db import database, connect_to_database, disconnect_from_database, create_tables, fetch_task_by_id
import uuid
import json

from .tasks import TASKS_TABLE, execute_task


# Асинхронный обработчик жизненного цикла приложения
async def app_lifespan(app):
    # Действия при старте приложения
    await database.connect()
    await create_tables()

    yield
    # Действия при остановке приложения
    # await disconnect_from_database()

app = FastAPI(lifespan=app_lifespan)
templates = Jinja2Templates(directory="app/templates")
# start_scheduler()

# Отображение списка задач
@app.get("/", response_class=HTMLResponse)
async def read_tasks(request: Request):
    query = "SELECT * FROM tasks"
    tasks = await database.fetch_all(query)
    return templates.TemplateResponse(
        "tasks.html",
        {"request": request, "tasks": tasks[::-1]}
    )

# Получение всех задач из базы данных
@app.get("/tasks", response_class=HTMLResponse)
async def get_tasks(request: Request):
    query = "SELECT * FROM tasks ORDER BY id ASC;"
    tasks = await database.fetch_all(query)
    return templates.TemplateResponse(
        "tasks.html",
        {"request": request, "tasks": tasks[::-1]}
    )

# Создание задачи через форму
@app.post("/tasks/create/", response_class=RedirectResponse)
async def create_task_form(request: Request,
                            query: str = Form(...),  # Получаем запрос через форму
                            parameters: str = Form(None),  # Получаем параметры как строку
                            scheduled_time: str = Form(None)):  # Получаем время запуска

    # Преобразование строки параметров в словарь, если они присутствуют
    parameters_dict = json.loads(parameters) if parameters else None

    # Преобразуем время запуска из строки в объект datetime, если оно указано
    scheduled_time = datetime.fromisoformat(scheduled_time) if scheduled_time else None

    # SQL-запрос для вставки задачи
    query_insert = """
    INSERT INTO tasks (query, parameters, status, scheduled_time)
    VALUES (:query, :parameters, 'pending', :scheduled_time)
    RETURNING id, query, parameters, status, created_at, updated_at, scheduled_time
    """

    # Подготовка значений для вставки
    values = {
        "query": query,
        "parameters": json.dumps(parameters_dict) if parameters_dict else None,
        "scheduled_time": scheduled_time or datetime.utcnow()  # Если время не указано, ставим текущее время
    }

    try:
        # Выполняем запрос вставки и получаем task_id
        task = await database.fetch_one(query_insert, values)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error inserting task: {str(e)}")

    await schedule_task(task['id'], task['scheduled_time'])

    return RedirectResponse(url="/tasks", status_code=303)

# Запуск задачи
@app.delete("/tasks/{task_id}/delete")
async def run_task(task_id: int):
    query = "DELETE FROM tasks WHERE id = :task_id"

    try:
        result = await database.execute(query, {"task_id": task_id})

        if result == 0:
            raise HTTPException(status_code=404, detail="Task not found")

        return {"message": f"Task {task_id} deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error deleting task: {str(e)}")

@app.post("/tasks/{task_id}/run")
async def run_task_now(task_id: int):
    query = f"SELECT * FROM {TASKS_TABLE} WHERE id = :task_id"
    task = await database.fetch_one(query, {"task_id": task_id})

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Обновляем статус задачи на "in_progress"
    update_query = f"UPDATE {TASKS_TABLE} SET status = 'in_progress' WHERE id = :task_id"
    await database.execute(update_query, {"task_id": task_id})

    # Выполняем задачу
    print(f"Running task {task_id} immediately")
    execute_task.send(task_id)  # Асинхронный запуск через Dramatiq

    return {"message": f"Task {task_id} is running now"}

@app.post("/tasks/{task_id}/reschedule/")
async def reschedule_task(task_id: int, scheduled_time: str):
    """
    Снова планирует выполнение задачи на указанное время.
    """

    task = await fetch_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Парсим время из строки
    try:
        new_scheduled_time = datetime.fromisoformat(scheduled_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO format.")

    # Обновляем запись задачи в БД
    update_query = """
       UPDATE tasks
       SET scheduled_time = :scheduled_time, status = 'scheduled', updated_at = :updated_at
       WHERE id = :task_id
       """
    await database.execute(
        query=update_query,
        values={
            "scheduled_time": new_scheduled_time,
            "updated_at": datetime.utcnow(),
            "task_id": task_id,
        }
    )

    # Добавляем задачу в планировщик
    await schedule_task(task_id, new_scheduled_time)

    return {"message": f"Task {task_id} rescheduled to {new_scheduled_time}"}

# Получение результатов задач
@app.get("/tasks/results", response_class=HTMLResponse)
async def get_task_results(request: Request):
    query = "SELECT * FROM task_results"
    results = await database.fetch_all(query)
    return templates.TemplateResponse(
        "results.html",
        {"request": request, "results": results},
    )

