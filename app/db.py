from databases import Database
import os
from datetime import datetime

# Подключение к PostgreSQL через databases
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@db/tasks")
database = Database(DATABASE_URL, min_size=10, max_size=50)

async def connect_to_database():
    """Подключение к базе данных."""
    if not database.is_connected:
        try:
            await database.connect()
            print("Connected to the database!")
        except Exception as e:
            print(f"Connection failed: {str(e)}")

async def disconnect_from_database():
    """Отключение от базы данных."""
    if database.is_connected:
        try:
            await database.disconnect()
            print("Disconnected from the database!")
        except Exception as e:
            print(f"Disconnection failed: {str(e)}")

# async def get_connection():
#     """Получаем подключение из пула."""
#     if not database.is_connected:
#         await connect_to_database()
#     return await database.connection()

async def create_tables():
    """Создание таблиц для хранения задач и их результатов."""
    create_tasks_table_query = """
    CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        sql_connstr TEXT DEFAULT NULL,  -- API endpoint, если тип задачи API
        query TEXT NULL, -- SQL запрос
        api_endpoint TEXT DEFAULT NULL,  -- API endpoint, если тип задачи API
        api_method VARCHAR(10) DEFAULT 'POST',
        task_type VARCHAR(50) NOT NULL, 
        parameters JSON DEFAULT NULL,
        status VARCHAR(50) DEFAULT 'scheduled',
        executed_count INT DEFAULT 0, -- Счетчик выполнений
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        scheduled_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    create_task_results_table_query = """
    CREATE TABLE IF NOT EXISTS task_results (
        id SERIAL PRIMARY KEY,
        task_id INT NOT NULL,
        status VARCHAR(50) NOT NULL,
        result TEXT,
        error_message TEXT DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
    );
    """
    try:
        # Выполняем запросы для создания таблиц
        await database.execute(create_tasks_table_query)
        await database.execute(create_task_results_table_query)
        print("Tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {str(e)}")

async def fetch_task_by_id(task_id: int):
    """Получение задачи по ID."""
    query = "SELECT * FROM tasks WHERE id = :id"
    result = await database.fetch_one(query, values={"id": task_id})
    return result

async def save_task_result(task_id: int, status: str, result: str):
    """Сохранение результата выполнения задачи."""
    query = """
    INSERT INTO task_results (task_id, status, result)
    VALUES (:task_id, :status, :result)
    """
    await database.execute(query, values={"task_id": task_id, "status": status, "result": result})

async def update_task_status(task_id: int, status: str):
    """Обновление статуса задачи."""
    query = """
    UPDATE tasks SET status = :status, updated_at = :updated_at WHERE id = :task_id
    """
    await database.execute(query, values={"task_id": task_id, "status": status, "updated_at": datetime.utcnow()})
