from datetime import datetime

from fastapi import FastAPI, Request, Form, HTTPException
from .tasks import execute_task
from .models import TaskCreate
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from .db import database, connect_to_database, disconnect_from_database, create_tables
import uuid
import json

async def app_lifespan(app):
    """Обработчик жизненного цикла приложения."""
    # Действия при старте приложения
    await connect_to_database()
    await create_tables()
    yield
    # Действия при остановке приложения
    await disconnect_from_database()

app = FastAPI(lifespan=app_lifespan)
templates = Jinja2Templates(directory="app/templates")

# Заглушка для данных задач
TASKS = [{"id": 1, "query": "SELECT * FROM users", "status": "pending"}]



@app.get("/", response_class=HTMLResponse)
async def read_tasks(request: Request):
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": TASKS})

@app.get("/tasks", response_class=HTMLResponse)
async def get_tasks(request: Request):
    query = "SELECT * FROM tasks"
    tasks = await database.fetch_all(query)
    return templates.TemplateResponse(
        "tasks.html",
        {"request": request, "tasks": tasks}
    )

# task create with api
@app.post("/tasks/create/api", response_class=HTMLResponse)
async def create_task(request: Request, task: TaskCreate):
    # Генерация уникального идентификатора задачи
    task_id = str(uuid.uuid4())

    # Сериализация параметров запроса в строку (если они есть)
    parameters_str = json.dumps(task.parameters) if task.parameters else None

    # Вставка задачи в базу данных
    query = """
    INSERT INTO tasks (query, parameters, status)
    VALUES (:query, :parameters, 'pending')
    """
    values = {
        "query": task.query,
        "parameters": parameters_str
    }

    try:
        # Вставляем данные в таблицу tasks
        await database.execute(query, values)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error inserting task: {str(e)}")

    return templates.TemplateResponse("task_created.html", {"request": request, "task_id": task_id})

# Создание задачи через форму
@app.post("/tasks/create/", response_class=HTMLResponse)
async def create_task(request: Request,
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
    RETURNING id
    """

    # Подготовка значений для вставки
    values = {
        "query": query,
        "parameters": json.dumps(parameters_dict) if parameters_dict else None,
        "scheduled_time": scheduled_time or datetime.utcnow()  # Если время не указано, ставим текущее время
    }

    try:
        # Выполняем запрос вставки и получаем task_id
        task_id = await database.fetch_val(query_insert, values)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error inserting task: {str(e)}")

    # Если задача должна быть выполнена немедленно
    if not scheduled_time or scheduled_time <= datetime.utcnow():
        execute_task.send(task_id)

    # Возвращаем HTML-страницу с task_id
    return templates.TemplateResponse("task_created.html", {"request": request, "task_id": task_id})

# Запуск задачи
@app.post("/tasks/{task_id}/run")
async def run_task(task_id: int):
    # Запуск задачи через актор Dramatiq
    print(f"Running task {task_id}")
    execute_task.send(task_id)  # Отправляем задачу в очередь
    return {"message": "Task started"}

# Получение результатов задач
@app.get("/tasks/results", response_class=HTMLResponse)
async def get_task_results(request: Request):
    query = "SELECT * FROM task_results"
    results = await database.fetch_all(query)
    return templates.TemplateResponse(
        "results.html",
        {"request": request, "results": results},
    )