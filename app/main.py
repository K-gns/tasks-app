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

# Task create with form
@app.post("/tasks/create/", response_class=HTMLResponse)
async def create_task(request: Request,
                      query: str = Form(...),  # Получаем запрос через форму
                      parameters: str = Form(None)):  # Получаем параметры как строку

    # Генерация уникального идентификатора задачи
    task_id = str(uuid.uuid4())

    # Преобразование строки параметров в словарь, если они присутствуют
    parameters_dict = json.loads(parameters) if parameters else None

    # Вставка задачи в базу данных
    query_insert = """
    INSERT INTO tasks (query, parameters, status)
    VALUES (:query, :parameters, 'pending')
    """
    values = {
        "query": query,
        "parameters": json.dumps(parameters_dict) if parameters_dict else None
    }

    try:
        # Вставляем данные в таблицу tasks
        await database.execute(query_insert, values)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error inserting task: {str(e)}")

    # После того как задача создана, перенаправляем на страницу подтверждения
    return templates.TemplateResponse("task_created.html", {"request": request, "task_id": task_id})


@app.post("/tasks/{task_id}/run")
async def run_task(task_id: int):
    # Имитация запуска задачи
    print(f"Running task {task_id}")
    return {"message": "Task started"}

@app.get("/tasks/results", response_class=HTMLResponse)
async def get_task_results(request: Request):
    query = "SELECT * FROM task_results"
    results = await database.fetch_all(query)
    return templates.TemplateResponse(
        "results.html",
        {"request": request, "results": results},
    )