from databases import Database
import os

# Подключение к PostgreSQL через databases
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pwd123@db/tasks")
try:
    database = Database(DATABASE_URL)
    print("Connected to the database!")
except Exception as e:
    print(f"Connection failed: {str(e)}")


async def create_tables():
    """Создание таблиц для хранения задач и их результатов."""
    # SQL-запрос для создания таблицы `tasks`
    create_tasks_table_query = """
    CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        query TEXT NOT NULL,
        parameters JSON DEFAULT NULL,
        status VARCHAR(50) DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    # SQL-запрос для создания таблицы `task_results`
    create_task_results_table_query = """
    CREATE TABLE IF NOT EXISTS task_results (
        id SERIAL PRIMARY KEY,
        task_id INT NOT NULL,
        status VARCHAR(50) NOT NULL,
        result TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
    );
    """
    # Выполняем запросы для создания таблиц
    await database.execute(create_tasks_table_query)
    await database.execute(create_task_results_table_query)

async def connect_to_database():
    """Подключение к базе данных."""
    await database.connect()

async def disconnect_from_database():
    """Отключение от базы данных."""
    await database.disconnect()
