from datetime import datetime
from dateutil import parser, tz

from fastapi import FastAPI, Request, Form, HTTPException, Body
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from .models import TaskForm, rescheduleReq
from .scheduler import start_scheduler, schedule_task

from .db import database, create_tables, fetch_task_by_id
import json

from .tasks import TASKS_TABLE, execute_task


# Обработчик жизненного цикла приложения
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
    query = "SELECT * FROM tasks ORDER BY id DESC;"
    tasks = await database.fetch_all(query)
    return templates.TemplateResponse(
        "tasks.html",
        {"request": request, "tasks": tasks}
    )

# Создание задачи через форму
@app.post("/tasks/create/", response_class=RedirectResponse)
async def create_task_form(request: Request,
                            task: TaskForm):  # Получаем время запуска

    # Преобразование строки параметров в словарь, если они присутствуют
    parameters_dict = json.loads(task.parameters) if task.parameters else None

    # Преобразуем время запуска из строки в объект datetime, если оно указано
    if task.scheduled_time:
        # Парсим время из ISO-формата
        scheduled_time = parser.isoparse(task.scheduled_time).replace(tzinfo=None)
    else:
        # Если время не указано, ставим текущее время
        scheduled_time = datetime.utcnow()


    # SQL-запрос для вставки задачи
    query_insert = """
    INSERT INTO tasks (task_type, query, sql_connstr, api_endpoint, api_method, parameters, status, scheduled_time)
    VALUES (:task_type, :query, :sql_connstr, :api_endpoint, :api_method, :parameters, 'pending', :scheduled_time)
    RETURNING id, query, parameters, status, created_at, updated_at, scheduled_time
    """

    # Подготовка значений для вставки
    values = {
        "task_type": task.task_type,
        "query": task.query,
        "sql_connstr": task.sql_connstr,
        "api_endpoint": task.api_endpoint,
        "api_method": task.api_method,
        "parameters": json.dumps(parameters_dict) if parameters_dict else None,
        "scheduled_time": scheduled_time
    }

    try:
        # Выполняем запрос вставки и получаем task_id
        taskRes = await database.fetch_one(query_insert, values)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error inserting task: {str(e)}")

    return RedirectResponse(url="/tasks", status_code=303)

# Результаты задач
@app.get("/tasks/results", response_class=HTMLResponse)
async def get_task_results(request: Request):
    query = "SELECT * FROM task_results ORDER BY id DESC"
    results = await database.fetch_all(query)
    return templates.TemplateResponse(
        "results.html",
        {"request": request, "results": results},
    )

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
    execute_task.send(task_id)  #  Запуск через Dramatiq

    return {"message": f"Task {task_id} is running now"}

@app.post("/tasks/{task_id}/reschedule/")
async def reschedule_task(task_id: int, request: rescheduleReq):
    """
    Снова планирует выполнение задачи на указанное время.
    """
    scheduled_time = request.scheduled_time

    task = await fetch_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Парсим время из строки
    try:
        new_scheduled_time = parser.isoparse(scheduled_time).replace(tzinfo=None)
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

#Тестовое
@app.post("/test")
async def test_task(request: Request):
    """Тестовый эндпоинт, который выводит весь запрос в консоль."""
    body = await request.json()  # Получаем JSON из тела запроса
    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    print(f"Received request at {current_time}, body: {body}")

    return {"message": f"Request received on test api (body: {body})"}

